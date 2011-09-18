if (Modernizr.geolocation) {
  navigator.geolocation.getCurrentPosition(function(location) {
    $('#venue_list')
      .data('ll', location.coords.latitude + "," + location.coords.longitude)
      .data('ll_act', location.coords.accuracy)
      .data('alt', location.coords.altitude + 0)
      .data('alt_acc', location.coords.altitudeAcc);
  });
}

$(function(){
  
  var $vl = $('#venue_list');
    
  var send_query = function(query_word) {
      var sent_data = {
          ll: $vl.data('ll'),
          ll_act: $vl.data('ll_act'),
          alt: $vl.data('alt'),
          alt_acc: $vl.data('alt_acc'),
          query: query_word
        };
      $.ajax({
          url:        "/venue/search",
          dataType:   "json", 
          data:       sent_data, 
          success:    function(data) {
                      var venues = data.response.groups[0].items;
                      
                      if (venues.length === 0) {
                        if(!sent_data.ll){
                          $list = '<p>This page doesn\'t have access to your location. We need that information to find relevant venues.</p>';
                        }
                        else{
                          $list = '<p>No venues found.</p>';
                        }
                      } else {
                        $list = $('<ul/>');
                        for (var i = 0; i < venues.length; i++) {
                          if (!!venues[i]) {
                            $list.append(tmpl('venue_list_item_tpl', venues[i]));
                          }
                        }          
                      }

          
                      $('#venue_map').empty().append($list);
                    }
      });
    };
  
  var delay = (function(){
    var timer = 0;
    return function(callback, ms){
      clearTimeout (timer);
      timer = setTimeout(callback, ms);
    };
  })();
  
  $('#venue_query').keyup(function() {
    $el = $(this); 
    delay(function() {
      send_query($el.val());
    }, 300);
  });

  $('#venue_map').delegate('a.add_venue', 'click', function(e) {
    e.preventDefault();
    var $el = $(this),
      venue = {
        id: $el.data('id'),
        name: $el.text()
      },
      hunt_id = $('#venue_list').data('hunt-id');
    $.get('/hunt/'+hunt_id+'/add_venue?venue_id=' + venue.id , function(data) {
      if (data === 'Ok') {
        $('#current_venues tbody').append(tmpl('venue_item_tpl', venue));
        
        $('#alerts').append(tmpl('success_alert_tpl', {message: 'Venue added succesfully'}));
      } else if (data === "Error") {
        console.log('todo mal');
      } else {
        console.log('todo muy mal');
      }
    });
  });
  
  $('#current_venues').delegate('a.close', 'click', function(e) {
    $el = $(this).closest('.venue-item');
      venue_id = $el.data('id');
      hunt_id = $('#venue_list').data('hunt-id');
    
    $.get('/hunt/'+hunt_id+'/remove_venue?venue_id=' + venue_id, function(data) {
      if (data === 'Ok') {
        $el.fadeOut();
        $('#alerts').append(tmpl('success_alert_tpl', {message: 'Venue deleted succesfully'}));
      } else if (data === "Error") {
        console.log('todo mal');
      } else {
        console.log('todo muy mal');
      }
    });
  });
  
  $('#current_venues').delegate('.venue_difficulty', 'change', function(e) {
    $el = $(this).closest('.venue-item');
      venue_id = $el.data('id');
      hunt_id = $('#venue_list').data('hunt-id');
    $.ajax({
      url: '/hunt/'+hunt_id+'/change_venue_difficulty?venue_id=' + venue_id + '&difficulty=' + $(this).val(),
      success: function(data) {
        if (data === 'Ok') {
          $('#alerts').append(tmpl('success_alert_tpl', {message: 'Difficulty changed succesfully'}));
        }
      }
    });
  });
  
  $("#alerts .alert-message").alert();
  
  $('#host').text('http://' + document.location.host + '/');

  var d = new Date();
  var gmtHours = -d.getTimezoneOffset()/60;
  $("#timezone_field").val(gmtHours);
  
  $('#start_time').datetimepicker();
  $('#end_time').datetimepicker();
});
