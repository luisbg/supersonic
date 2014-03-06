var player;

$(document).ready(function () {
    $('#player').mediaelementplayer({
        success: function(mediaElement, domObject) {
            player = mediaElement;
            player.play();

            player.addEventListener('ended', function(){
                EOS();
            });

        },
        error: function() {
            alert('Error setting media!');
        }
    });
});

function EOS() {
    alert('End of stream');
}
