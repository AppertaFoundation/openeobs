# NHMobileForm contains utilities for working with the nh_eobs_mobile
# observation form
class NHMobileForm extends NHMobile

  constructor: () ->
    # find the form on the page
    @form = document.getElementsByTagName('form')?[0]
    @form_timeout = 240*1000
    ptn_name = document.getElementById('patientName')
    @patient_name_el = ptn_name.getElementsByTagName('a')[0]
    @patient_name = () ->
      @patient_name_el.text
    self = @
    @setup_event_listeners(self)
    super()

  setup_event_listeners: (self) ->
   
    # for each input in the form set up the event listeners
    for input in @form.elements
      do () ->
        switch input.localName
          when 'input'
            switch input.getAttribute('type')
              when 'number'
                input.addEventListener('change', self.validate)
                input.addEventListener('change', self.trigger_actions)
              when 'submit' then input.addEventListener('click', self.submit)
              when 'reset' then input.addEventListener('click',
                  self.cancel_notification)
              when 'radio' then input.addEventListener('click',
                  self.trigger_actions)
          when 'select' then input.addEventListener('change',
            self.trigger_actions)


    document.addEventListener 'form_timeout', (event) ->
      self.handle_timeout(self, self.form.getAttribute('task-id'))
    window.timeout_func = () ->
      timeout = new CustomEvent('form_timeout', {'detail': 'form timed out'})
      document.dispatchEvent(timeout)
    window.form_timeout = setTimeout(window.timeout_func, @form_timeout)

    document.addEventListener 'post_score_submit', (event) ->
      form_elements = (element for element in self.form.elements when not
        element.classList.contains('exclude'))
      endpoint = event.detail
      self.submit_observation(self,
        form_elements, endpoint, self.form.getAttribute('ajax-args'))

    document.addEventListener 'partial_submit', (event) ->
      form_elements = (element for element in self.form.elements when not
        element.classList.contains('exclude'))
      reason = document.getElementsByName('partial_reason')[0]
      if reason
        form_elements.push(reason)
      details = event.detail
      self.submit_observation(self, form_elements, details.action,
        self.form.getAttribute('ajax-args'))
      dialog_id = document.getElementById(details.target)
      cover = document.getElementById('cover')
      document.getElementsByTagName('body')[0].removeChild(cover)
      dialog_id.parentNode.removeChild(dialog_id)

    @patient_name_el.addEventListener 'click', (event) ->
      event.preventDefault()
      input = if event.srcElement then event.srcElement else event.target
      patient_id = input.getAttribute('patient-id')
      if patient_id
        self.get_patient_info(patient_id, self)
      else
        can_btn = '<a href="#" data-action="close" '+
          'data-target="patient_info_error">Cancel</a>'
        new window.NH.NHModal('patient_info_error',
        'Error getting patient information',
        '',
        [can_btn],
        0, document.getElementsByTagName('body')[0])



  validate: (event) =>
    event.preventDefault()
    @.reset_form_timeout(@)
    input = if event.srcElement then event.srcElement else event.target
    @reset_input_errors(input)
    value = parseFloat(input.value)
    min = parseFloat(input.getAttribute('min'))
    max = parseFloat(input.getAttribute('max'))
    if typeof(value) isnt 'undefined' and not isNaN(value) and value isnt ''
      if input.getAttribute('type') is 'number'
        if input.getAttribute('step') is '1' and value % 1 isnt 0
          @.add_input_errors(input, 'Must be whole number')
          return
        if value < min
          @.add_input_errors(input, 'Input too low')
          return
        if value > max
          @.add_input_errors(input, 'Input too high')
          return
        if input.getAttribute('data-validation')
          criterias = eval(input.getAttribute('data-validation'))
          for criteria in criterias
            crit_target = criteria['condition']['target']
            crit_val = criteria['condition']['value']
            target_input = document.getElementById(crit_target)
            target_input_value = target_input?.value
            other_input = document.getElementById(crit_val)
            other_input_value = other_input?.value
            operator = criteria['condition']['operator']
            if target_input?.getAttribute('type') is 'number'
              other_input_value = parseFloat(other_input_value)
            cond = target_input_value + ' ' + operator + ' ' + other_input_value
            if eval(cond)
              @.reset_input_errors(other_input)
              continue
            if typeof(other_input_value) isnt 'undefined' and
            not isNaN(other_input_value) and other_input_value isnt ''
              @.add_input_errors(target_input, criteria['message']['target'])
              @.add_input_errors(other_input, criteria['message']['value'])
              continue
            else
              @.add_input_errors(target_input, criteria['message']['target'])
              @.add_input_errors(other_input, 'Please enter a value')
              continue
    else
     # to be continued

  trigger_actions: (event) =>
    # event.preventDefault()
    @.reset_form_timeout(@)
    input = if event.srcElement then event.srcElement else event.target
    value = input.value
    if input.getAttribute('type') is 'radio'
      for el in document.getElementsByName(input.name)
        if el.value isnt value
          el.classList.add('exclude')
        else
          el.classList.remove('exclude')
    if value is ''
      value = 'Default'
    if input.getAttribute('data-onchange')
      actions = eval(input.getAttribute('data-onchange'))
      for action in actions
        for condition in action['condition']
          if condition[0] not in ['True', 'False'] and
          typeof condition[0] is 'string'
            condition[0] = 'document.getElementById("'+condition[0]+'").value'
          if condition[2] not in ['True', 'False'] and
          typeof condition[2] is 'string' and condition[2] isnt ''
            condition[2] = 'document.getElementById("'+condition[2]+'").value'
          if condition[2] in ['True', 'False', '']
            condition[2] = "'"+condition[2]+"'"
        mode = ' && '
        conditions = []
        for condition in action['condition']
          if typeof condition is 'object'
            conditions.push(condition.join(' '))
          else
            mode = condition
        conditions = conditions.join(mode)
        if eval(conditions)
          if action['action'] is 'hide'
            for field in action['fields']
              @.hide_triggered_elements(field)
          if action['action'] is 'show'
            for field in action['fields']
              @.show_triggered_elements(field)
    return
   
  submit: (event) =>
    event.preventDefault()
    @.reset_form_timeout(@)
    form_elements =
      (element for element in @form.elements \
        when not element.classList.contains('exclude'))
    invalid_elements =
      (element for element in form_elements \
        when element.classList.contains('error'))
    empty_elements =
      (element for element in form_elements when not element.value)
    if invalid_elements.length<1 and empty_elements.length<1
      # do something with the form
      @submit_observation(@, form_elements, @form.getAttribute('ajax-action'),
        @form.getAttribute('ajax-args'))
    else if invalid_elements.length>0
      msg = '<p class="block">The form contains errors, please correct '+
        'the errors and resubmit</p>'
      btn = '<a href="#" data-action="close" data-target="invalid_form">'+
        'Cancel</a>'
      new window.NH.NHModal('invalid_form', 'Form contains errors',
        msg, [btn], 0, @.form)
    else
      # display the partial obs dialog
      @display_partial_reasons(@)

  display_partial_reasons: (self) =>
    Promise.when(@call_resource(@.urls.json_partial_reasons())).then (data) ->
      options = ''
      for option in data[0][0]
        option_val = option[0]
        option_name = option[1]
        options += '<option value="'+option_val+'">'+option_name+'</option>'
      select = '<select name="partial_reason">'+options+'</select>'
      con_btn = '<a href="#" data-target="partial_reasons" '+
        'data-action="partial_submit" '+
        'data-ajax-action="json_task_form_action">Confirm</a>'
      can_btn = '<a href="#" data-action="close" '+
        'data-target="partial_reasons">Cancel</a>'
      msg = '<p class="block">Please state reason for '+
        'submitting partial observation</p>'
      new window.NH.NHModal('partial_reasons', 'Submit partial observation',
        msg+select, [can_btn, con_btn], 0, self.form)

  submit_observation: (self, elements, endpoint, args) =>
    # turn form data in to serialised string and ping off to server
    serialised_string = (el.name+'='+el.value for el in elements).join("&")
    url = @.urls[endpoint].apply(this, args.split(','))
    Promise.when(@call_resource(url, serialised_string)).then (server_data) ->
      data = server_data[0][0]
      if data and data.status is 3
        can_btn = '<a href="#" data-action="close" '+
          'data-target="submit_observation">Cancel</a>'
        act_btn = '<a href="#" data-target="submit_observation" '+
          'data-action="submit" data-ajax-action="'+
          data.modal_vals['next_action']+'">Submit</a>'
        new window.NH.NHModal('submit_observation',
          data.modal_vals['title'] + ' for ' + self.patient_name() + '?',
          data.modal_vals['content'],
          [can_btn, act_btn], 0, self.form)
        if 'clinical_risk' of data.score
          sub_ob = document.getElementById('submit_observation')
          cls = 'clinicalrisk-'+data.score['clinical_risk'].toLowerCase()
          sub_ob.classList.add(cls)
      else if data and data.status is 1
        triggered_tasks = ''
        buttons = ['<a href="'+self.urls['task_list']().url+
          '" data-action="confirm">Go to My Tasks</a>']
        if data.related_tasks.length is 1
          triggered_tasks = '<p>' + data.related_tasks[0].summary + '</p>'
          rt_url = self.urls['single_task'](data.related_tasks[0].id).url
          buttons.push('<a href="'+rt_url+'">Confirm</a>')
        else if data.related_tasks.length > 1
          tasks = ''
          for task in data.related_tasks
            st_url = self.urls['single_task'](task.id).url
            tasks += '<li><a href="'+st_url+'">'+task.summary+'</a></li>'
          triggered_tasks = '<ul class="menu">'+tasks+'</ul>'
        pos = '<p>Observation was submitted</p>'
        os = 'Observation successfully submitted'
        task_list = if triggered_tasks then triggered_tasks else pos
        title = if triggered_tasks then 'Action required' else os
        new window.NH.NHModal('submit_success', title ,
          task_list, buttons, 0, self.form)
      else if data and data.status is 4
        btn = '<a href="'+self.urls['task_list']().url+
          '" data-action="confirm" data-target="cancel_success">'+
          'Go to My Tasks</a>'
        new window.NH.NHModal('cancel_success', 'Task successfully cancelled',
          '', [btn], 0, self.form)
      else
        btn = '<a href="#" data-action="close" '+
          'data-target="submit_error">Cancel</a>'
        new window.NH.NHModal('submit_error', 'Error submitting observation',
          'Server returned an error',
          [btn], 0, self.form)

  handle_timeout: (self, id) ->
    can_id = self.urls['json_cancel_take_task'](id)
    Promise.when(self.call_resource(can_id)).then (server_data) ->
      msg = '<p class="block">Please pick the task again from the task list '+
        'if you wish to complete it</p>'
      btn = '<a href="'+self.urls['task_list']().url+
        '" data-action="confirm">Go to My Tasks</a>'
      new window.NH.NHModal('form_timeout', 'Task window expired', msg,
        [btn], 0, document.getElementsByTagName('body')[0])

  cancel_notification: (self) =>
    opts = @.urls.ajax_task_cancellation_options()
    Promise.when(@call_resource(opts)).then (data) ->
      options = ''
      for option in data[0][0]
        option_val = option.id
        option_name = option.name
        options += '<option value="'+option_val+'">'+option_name+'</option>'
      select = '<select name="reason">'+options+'</select>'
      msg = '<p>Please state reason for cancelling task</p>'
      can_btn = '<a href="#" data-action="close" '+
        'data-target="cancel_reasons">Cancel</a>'
      con_btn = '<a href="#" data-target="cancel_reasons" '+
        'data-action="partial_submit" '+
        'data-ajax-action="cancel_clinical_notification">Confirm</a>'
      new window.NH.NHModal('cancel_reasons', 'Cancel task', msg+select,
        [can_btn, con_btn], 0, document.getElementsByTagName('form')[0])

  reset_form_timeout: (self) ->
    clearTimeout(window.form_timeout)
    window.form_timeout = setTimeout(window.timeout_func, self.form_timeout)

  reset_input_errors: (input) ->
    container_el = input.parentNode.parentNode
    error_el = container_el.getElementsByClassName('errors')[0]
    container_el.classList.remove('error')
    input.classList.remove('error')
    error_el.innerHTML = ''

  add_input_errors: (input, error_string) ->
    container_el = input.parentNode.parentNode
    error_el = container_el.getElementsByClassName('errors')[0]
    container_el.classList.add('error')
    input.classList.add('error')
    error_el.innerHTML = '<label for="'+input.name+'" class="error">'+
      error_string+'</label>'

  hide_triggered_elements: (field) ->
    el = document.getElementById('parent_'+field)
    el.style.display = 'none'
    inp = document.getElementById(field)
    inp.classList.add('exclude')

  show_triggered_elements: (field) ->
    el = document.getElementById('parent_'+field)
    el.style.display = 'block'
    inp = document.getElementById(field)
    inp.classList.remove('exclude')



if !window.NH
  window.NH = {}
window?.NH.NHMobileForm = NHMobileForm

