$(document).ready(function () {
    // Get the data-show2fa attribute from the body tag
    var show2FA = $('body').data('show2fa');

    // Debugging: log the value of show2FA
    console.log("show2FA value: ", show2FA);

    // Check if 2FA should be shown (compare loosely)
    if (show2FA == true || show2FA == "true") {  // Accept both boolean and string
        console.log("Showing 2FA modal");
        $('#twoFactorModal').modal('show');
    } else {
        console.log("Not showing 2FA modal");
    }
});
