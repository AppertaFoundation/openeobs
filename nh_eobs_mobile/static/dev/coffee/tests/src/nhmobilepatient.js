var NHMobilePatient,
  extend = function(child, parent) { for (var key in parent) { if (hasProp.call(parent, key)) child[key] = parent[key]; } function ctor() { this.constructor = child; } ctor.prototype = parent.prototype; child.prototype = new ctor(); child.__super__ = parent.prototype; return child; },
  hasProp = {}.hasOwnProperty;

NHMobilePatient = (function(superClass) {
  extend(NHMobilePatient, superClass);

  function NHMobilePatient() {
    var data_id, i, len, obs, obs_menu, self, tab, table_view, tabs, tabs_el;
    self = this;
    NHMobilePatient.__super__.constructor.call(this);
    obs_menu = document.getElementById('obsMenu');
    obs_menu.style.display = 'none';
    table_view = document.getElementById('table-content');
    table_view.style.display = 'none';
    obs = document.getElementsByClassName('obs');
    obs[0].addEventListener('click', this.show_obs_menu);
    tabs_el = document.getElementsByClassName('tabs');
    tabs = tabs_el[0].getElementsByTagName('a');
    for (i = 0, len = tabs.length; i < len; i++) {
      tab = tabs[i];
      tab.addEventListener('click', this.handle_tabs);
    }
    data_id = document.getElementById('graph-content').getAttribute('data-id');
    Promise.when(this.call_resource(this.urls['ajax_get_patient_obs'](data_id))).then(function(server_data) {
      return self.draw_graph(self, server_data);
    });
  }

  NHMobilePatient.prototype.handle_tabs = function(event) {
    var i, len, tab, tabs;
    event.preventDefault();
    tabs = document.getElementsByClassName('tabs')[0].getElementsByTagName('a');
    for (i = 0, len = tabs.length; i < len; i++) {
      tab = tabs[i];
      tab.classList.remove('selected');
    }
    document.getElementById('graph-content').style.display = 'none';
    document.getElementById('table-content').style.display = 'none';
    event.srcElement.classList.add('selected');
    return $(event.srcElement.getAttribute('href')).show();
  };

  NHMobilePatient.prototype.show_obs_menu = function(event) {
    var obs_menu;
    event.preventDefault();
    obs_menu = document.getElementById('obsMenu');
    return new window.NH.NHModal('obs_menu', 'Pick an observation for ', '<ul class="menu">' + obs_menu.innerHTML + '</ul>', ['<a href="#" data-action="close" data-target="obs_menu">Cancel</a>'], 0, document.getElementsByTagName('body')[0]);
  };

  NHMobilePatient.prototype.draw_graph = function(self, server_data) {
    var bp_graph, chart, context, controls, element_for_chart, focus, graph_content, graph_tabs, obs, oxy_graph, pulse_graph, resp_rate_graph, score_graph, svg, tabular_obs, temp_graph;
    element_for_chart = 'chart';
    obs = server_data[0][0].obs.reverse();
    if (obs.length > 0) {
      svg = new window.NH.NHGraphLib('#' + element_for_chart);
      resp_rate_graph = new window.NH.NHGraph();
      resp_rate_graph.options.keys = ['respiration_rate'];
      resp_rate_graph.options.label = 'RR';
      resp_rate_graph.options.measurement = '/min';
      resp_rate_graph.axes.y.min = 0;
      resp_rate_graph.axes.y.max = 60;
      resp_rate_graph.options.normal.min = 12;
      resp_rate_graph.options.normal.max = 20;
      resp_rate_graph.style.dimensions.height = 250;
      resp_rate_graph.style.data_style = 'linear';
      resp_rate_graph.style.label_width = 60;
      oxy_graph = new window.NH.NHGraph();
      oxy_graph.options.keys = ['indirect_oxymetry_spo2'];
      oxy_graph.options.label = 'Spo2';
      oxy_graph.options.measurement = '%';
      oxy_graph.axes.y.min = 70;
      oxy_graph.axes.y.max = 100;
      oxy_graph.options.normal.min = 96;
      oxy_graph.options.normal.max = 100;
      oxy_graph.style.dimensions.height = 200;
      oxy_graph.style.axis.x.hide = true;
      oxy_graph.style.data_style = 'linear';
      oxy_graph.style.label_width = 60;
      temp_graph = new window.NH.NHGraph();
      temp_graph.options.keys = ['body_temperature'];
      temp_graph.options.label = 'Temp';
      temp_graph.options.measurement = '°C';
      temp_graph.axes.y.min = 15;
      temp_graph.axes.y.max = 50;
      temp_graph.options.normal.min = 35;
      temp_graph.options.normal.max = 37.1;
      temp_graph.style.dimensions.height = 200;
      temp_graph.style.axis.x.hide = true;
      temp_graph.style.data_style = 'linear';
      temp_graph.style.label_width = 60;
      pulse_graph = new window.NH.NHGraph();
      pulse_graph.options.keys = ['pulse_rate'];
      pulse_graph.options.label = 'HR';
      pulse_graph.options.measurement = '/min';
      pulse_graph.axes.y.min = 30;
      pulse_graph.axes.y.max = 200;
      pulse_graph.options.normal.min = 50;
      pulse_graph.options.normal.max = 100;
      pulse_graph.style.dimensions.height = 200;
      pulse_graph.style.axis.x.hide = true;
      pulse_graph.style.data_style = 'linear';
      pulse_graph.style.label_width = 60;
      bp_graph = new window.NH.NHGraph();
      bp_graph.options.keys = ['blood_pressure_systolic', 'blood_pressure_diastolic'];
      bp_graph.options.label = 'BP';
      bp_graph.options.measurement = 'mmHg';
      bp_graph.axes.y.min = 30;
      bp_graph.axes.y.max = 260;
      bp_graph.options.normal.min = 150;
      bp_graph.options.normal.max = 151;
      bp_graph.style.dimensions.height = 200;
      bp_graph.style.axis.x.hide = true;
      bp_graph.style.data_style = 'range';
      bp_graph.style.label_width = 60;
      score_graph = new window.NH.NHGraph();
      score_graph.options.keys = ['score'];
      score_graph.style.dimensions.height = 200;
      score_graph.style.data_style = 'stepped';
      score_graph.axes.y.min = 0;
      score_graph.axes.y.max = 22;
      score_graph.drawables.background.data = [
        {
          "class": "green",
          s: 1,
          e: 4
        }, {
          "class": "amber",
          s: 4,
          e: 6
        }, {
          "class": "red",
          s: 6,
          e: 22
        }
      ];
      score_graph.style.label_width = 60;
      tabular_obs = new window.NH.NHTable();
      tabular_obs.keys = [
        {
          key: 'avpu_text',
          title: 'AVPU'
        }, {
          key: 'oxygen_administration_flag',
          title: 'On Supplemental O2'
        }
      ];
      tabular_obs.title = 'Tabular values';
      focus = new window.NH.NHFocus();
      context = new window.NH.NHContext();
      focus.graphs.push(resp_rate_graph);
      focus.graphs.push(oxy_graph);
      focus.graphs.push(temp_graph);
      focus.graphs.push(pulse_graph);
      focus.graphs.push(bp_graph);
      focus.tables.push(tabular_obs);
      focus.title = 'Individual values';
      focus.style.padding.right = 0;
      context.graph = score_graph;
      context.title = 'NEWS Score';
      svg.focus = focus;
      svg.context = context;
      svg.options.controls.date.start = document.getElementById('start_date');
      svg.options.controls.date.end = document.getElementById('end_date');
      svg.options.controls.time.start = document.getElementById('start_time');
      svg.options.controls.time.end = document.getElementById('end_time');
      svg.options.controls.rangify = document.getElementById('rangify');
      svg.table.element = '#table';
      svg.table.keys = [
        {
          title: 'Respiration Rate',
          keys: ['respiration_rate']
        }, {
          title: 'O2 Saturation',
          keys: ['indirect_oxymetry_spo2']
        }, {
          title: 'Body Temperature',
          keys: ['body_temperature']
        }, {
          title: 'Blood Pressure Systolic',
          keys: ['blood_pressure_systolic']
        }, {
          title: 'Blood Pressure Diastolic',
          keys: ['blood_pressure_diastolic']
        }, {
          title: 'Pulse Rate',
          keys: ['pulse_rate']
        }, {
          title: 'AVPU',
          keys: ['avpu_text']
        }, {
          title: 'Patient on Supplemental O2',
          keys: ['oxygen_administration_flag']
        }, {
          title: 'Inspired Oxygen',
          keys: [
            {
              title: 'Flow Rate',
              keys: ['flow_rate']
            }, {
              title: 'Concentration',
              keys: ['concentration']
            }, {
              title: 'Device',
              keys: ['device_id']
            }, {
              title: 'CPAP PEEP',
              keys: ['cpap_peep']
            }, {
              title: 'NIV iPAP',
              keys: ['niv_ipap']
            }, {
              title: 'NIV ePAP',
              keys: ['niv_epap']
            }, {
              title: 'NIV Backup Rate',
              keys: ['niv_backup']
            }
          ]
        }
      ];
      svg.data.raw = obs;
      svg.init();
      return svg.draw();
    } else {
      graph_content = document.getElementById('graph-content');
      controls = document.getElementById('controls');
      chart = document.getElementById(element_for_chart);
      graph_tabs = graph_content.parentNode.getElementsByClassName('tabs');
      controls.style.display = 'none';
      chart.innerHTML = '<h2>No observation data available for patient</h2>';
      return graph_tabs[0].style.display = 'none';
    }
  };

  return NHMobilePatient;

})(NHMobile);

if (!window.NH) {
  window.NH = {};
}

if (typeof window !== "undefined" && window !== null) {
  window.NH.NHMobilePatient = NHMobilePatient;
}
