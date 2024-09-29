$(document).ready(function () {
    // Get the data-show2fa attribute from the body tag
    var show2FA = $('body').data('show2fa');


    // Check if 2FA should be shown (compare loosely)
    if (show2FA == true || show2FA == "true") {  // Accept both boolean and string
        $('#twoFactorModal').modal('show');
    } else {
    }
});
