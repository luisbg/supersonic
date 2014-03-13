var player;

$(document).ready(function () {
    $('#player').mediaelementplayer({
        success: function(mediaElement, domObject) {
            player = mediaElement;
            get_active();
            play();

            player.addEventListener('ended', function(){
                EOS();
            });
        },
        error: function() {
            alert('Error setting media!');
        }
    });

    $("#music_library").treetable({ expandable: true });
    update_repeat_mode(1);

    $('a#next').bind('click', function() {
        $.getJSON('/_next', { }, function (data) {
            if (data.result) {
                get_active();
                play();
            }
        });

        return false;
    });

    $('a#prev').bind('click', function() {
        $.getJSON('/_prev', { }, function (data) {
            if (data.result) {
                get_active();
                play();
            }
        });

        return false;
    });

    $('a#add').bind('click', function(idn) {
        var ref = $(this).attr("href");
        $.getJSON('/_add/' + ref, { }, function (data) {
            update_playlist();
        });

        return false;
    });

    $('a#clear').bind('click', function() {
        $.getJSON('/_clear', function (data) {
            if (data.result) {
                update_playlist();
                }
        });

        return false;
    });

    $('a#shuffle').bind('click', function() {
        $.getJSON('/_shuffle', function (data) {
            if (data.result) {
                update_playlist();
                get_active();
                }
        });

        return false;
    });

    $('a#repeat').bind('click', function(s) {
        update_repeat_mode(0);
        return false;
    });
});

$(document).on('click', 'a#remove', function() {
    var idn = $(this).attr("href").slice(1);
    $.getJSON('/_remove/' + idn, { }, function (data) {
        update_playlist();
    });

    return false;
});

$(document).on('click', 'a#play', function() {
    var idn = $(this).attr("href").slice(1);
    $.getJSON('/_play/' + idn, { }, function (data) {
        if (data.result) {
            get_active();
            play();
        }
    });

    return false;
});


function EOS() {
    // play next track in the playlist
    $.getJSON('/_next', { }, function (data) {
        if (data.result) {
            get_active();
            play();
        }
    });
}

function get_active() {
    $.getJSON('/_get_active', { },
              function(data) {
                  player.setSrc(data.result[3]);
                  play();
                  $("#track_info").text(data.result[0] + " - " + data.result[2]);
              });
    return false;
}

function play() {
    player.load();
    player.play();
}

function update_playlist() {
    $.getJSON('/_get_playlist', { },
              function(data) {
                  $("#playlist").text("");
                  $("#playlist").append(data.result);
              });
}

function update_repeat_mode(get) {
    $.getJSON('/_repeat/' + get, { },
              function (data) {
                  var mode_text = "";
                  switch (data.result)
                  {
                  case 0:
                      mode_text = "Repeat Off";
                      break;
                  case 1:
                      mode_text = "Repeat All";
                      break;
                  case 2:
                      mode_text = "Repeat One";
                      break;
                  default:
                      break;
                  }

                  $('a#repeat').text(mode_text);
              });
}
