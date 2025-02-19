$(document).ready(function () {
	
   $("#add-form").validate({
       debug: false,
       rules: {
           category: {
               required: function () {
                   if ($("#id_category option[value='']")) {
                       return true;
                   } else {
                       return false;
                   }
               }
           },
	       release: {
	    	      required: true,
	    	      min: 1900
	       },
	       duration: {
	    	   time24: true
	       },
       },
       messages: {
           category: "Select a genre",
           release: "Year must be 1900 or more",
           duration: "Invalid time format",
       },
   });

   $.validator.addMethod("time24", function(value, element) {
	    if (!/^([01]?[0-9]|2[0-3])(:[0-5][0-9])$/.test(value)) return false;
	    var parts = value.split(':');
	    if (parts[0] > 23 || parts[1] > 59) return false;
	    return true;
	}, "Invalid time format.");

});
