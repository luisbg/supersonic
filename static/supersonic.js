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
        var idn = $(this).attr("href");
        $.getJSON('/_add/' + idn, { }, function (data) {
            update_playlist();
        });

        return false;
    });
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
