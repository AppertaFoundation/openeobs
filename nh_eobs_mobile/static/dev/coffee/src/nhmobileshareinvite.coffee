# NHMobileShareInvite
# Allows user to accept invitations to follow another user's patients via a
# notification in patient list

class NHMobileShareInvite extends NHMobile

  # On initialisation
  # - Find all invitations to follow a patient in the patient list
  # - Add an EventListener to the invite's element to present modal for invite
  constructor: (patient_list) ->
    self = @
    invite_list = patient_list.getElementsByClassName('share_invite')
    for invite in invite_list
      invite.addEventListener 'click', (event) ->
        if not event.handled
          btn = if event.srcElement then event.srcElement else event.target
          activity_id = parseInt(btn.getAttribute('data-invite-id'))
          self.handle_invite_click(self, activity_id)
          event.handled = true
    document.addEventListener 'accept_invite', (event) ->
      if not event.handled
        activity_id = event.detail.invite_id
        self.handle_accept_button_click(self, activity_id)
        event.handled = true
    super()

  # On the user clicking the invitation to follow another user's patients
  # - Contact the server with the ID of the invite activity
  # - The server will return a list of patients that are to be shared
  # - Show the patients in a modal with a button accept the invitation
  handle_invite_click: (self, activity_id) ->
    url = self.urls.json_invite_patients(activity_id)
    urlmeth = url.method
    Promise.when(self.process_request(urlmeth, url.url)).then (server_data) ->
      data = server_data[0]
      pt_list = '<ul>'
      for pt in data
        pt_obj = '<li>'+
          '<div class="task-meta">'+
          '<div class="task-right">'+
          '<p class="aside">'+pt['ews_deadline']+'</p></div>'+
          '<div class="task-left">'+
          '<strong>'+pt['name']+'</strong>'+
          '('+pt['ews_score']+' <i class="icon-'+
          pt['ews_trend']+'-arrow"></i> )'+
          '<em>'+pt['location']+', '+pt['parent_location']+'</em>'+
          '</div>'+
          '</div>'+
          '</li>'
        pt_list += pt_obj
      pt_list += '</ul>'
      acpt_btn = '<a href="#" data-action="accept" data-target="accept_invite"'+
        'data-ajax-action="json_accept_invite" '+
        'data-invite-id="'+activity_id+'">Accept</a>'
      can_btn = '<a href="#" data-action="close" data-target="assign_nurse"'+
        '>Cancel</a>'
      btns = [acpt_btn, can_btn]
      body = document.getElementsByTagName('body')[0]
      return new window.NH.NHModal('accept_invite',
        'Accept invitation to follow patients?',
        pt_list, btns, 0, body)
    return true

  handle_accept_button_click: (self, activity_id) ->
    url = self.urls.json_accept_patients(activity_id)
    urlmeth = url.method
    btns = ['<a href="#" data-action="close" data-target="assign_nurse"'+
        '>Cancel</a>']
    body = document.getElementsByTagName('body')[0]
    Promise.when(self.process_request(urlmeth, url.url)).then (server_data) ->
      data = server_data[0][0]
      if data['status']
        invites = document.getElementsByClassName('share_invite')
        invite = (i for i in invites when \
          parseInt(i.getAttribute('data-invite-id')) is activity_id)[0]
        invite.parentNode.removeChild(invite)
        return new window.NH.NHModal('invite_success',
          'Successfully accepted patients',
          'Now following '+data['count']+' patients from '+data['user'],
          btns, 0, body)
      else
        return new window.NH.NHModal('invite_error',
          'Error accepting patients',
          'There was an error accepting the invite to follow, Please try again',
          btns, 0, body)

if !window.NH
  window.NH = {}
window?.NH.NHMobileShareInvite = NHMobileShareInvite