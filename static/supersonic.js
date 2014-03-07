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

    $('a#next').bind('click', function() {
        $.getJSON('/_next', { }, function (data) {});
        get_active();
        play();
        return false;
    });

    $('a#prev').bind('click', function() {
        $.getJSON('/_prev', { }, function (data) {});
        get_active();
        play();
        return false;
    });
});

function EOS() {
    player.play();
    // alert('End of stream');
}

function get_active() {
    $.getJSON('/_get_active', { },
              function(data) {
                  player.setSrc(data.result[3]);
                  play();
                  $("#result").text(data.result[1] + " - " + data.result[2]);
              });
    return false;
}

function play() {
    player.load();
    player.play();
}
