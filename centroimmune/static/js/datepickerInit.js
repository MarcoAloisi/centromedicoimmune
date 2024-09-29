$(document).ready(function() {
    // Initialize the Date Picker
    $("#datepicker").datepicker({
      dateFormat: "dd-mm-yy",
      changeMonth: true,
      changeYear: true,
      yearRange: "1900:2024"
    });
  });
  