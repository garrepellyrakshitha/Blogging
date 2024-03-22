$(document).ready(function () {
  //Custom method for date comparison
  jQuery.validator.addMethod(
    "greaterThan",
    function (value, element, params) {
      if (!/Invalid|NaN/.test(new Date(value))) {
        return new Date(value) > new Date($(params).val());
      }
      return (
        (isNaN(value) && isNaN($(params).val())) ||
        Number(value) > Number($(params).val())
      );
    },
    "Must be greater than {0}."
  );

  // Custom methods only for letters
  jQuery.validator.addMethod(
    "lettersonly",
    function (value, element) {
      return this.optional(element) || /^[a-z\s]+$/i.test(value);
    },
    "Only alphabetical characters"
  );

  $("#blog_form").validate();
  $("#room_form").validate({
    rules: {
      room_name: {
        remote: {
          url: "/is-room-not-exist",
          type: "get",
          data: {
            room_id: $("#room_id").val(),
          },
        },
      },
    },
    messages: {
      room_name: {
        remote: "Room Name already Exist",
      },
    },
  });

  $("#sub_admin_form").validate({
    rules: {
      email: {
        email: true,
        remote: {
          url: "/is-sub-admin-email-exist",
          type: "get",
          data: {
            sub_admin_id: $("#sub_admin_id").val(),
          },
        },
      },
    },
    messages: {
      email: {
        remote: "Sub admin email exist",
      },
    },
  });

  $("#student_registration").validate({
    rules: {
      email: {
        email: true,
        remote: {
          url: "/is-student-email-exist",
          type: "get",
        },
      },
      password: {
        minlength: 3,
      },
      confirm_password: {
        minlength: 3,
        equalTo: "#password",
      },
    },
    messages: {
      email: {
        remote: "Email already registered",
      },
      confirm_password: {
        equalTo: "Password and confirm password doesn't match",
      },
    },
  });

  $("#admin-change-password").validate({
    rules: {
      password: {
        minlength: 3,
      },
      confirm_password: {
        minlength: 3,
        equalTo: "#password",
      },
    },
    messages: {
      confirm_password: {
        equalTo: "Password and confirm password doesn't match",
      },
    },
  });

  $("#restaurent-login").validate();

  $("#admin-login-form").validate();

  $("#restaurent-registration").validate({
    rules: {
      login_email: {
        email: true,
        remote: {
          url: "/is-user-email-exist",
          type: "get",
        },
      },
      password: {
        minlength: 3,
      },
      confirm_password: {
        minlength: 3,
        equalTo: "#password",
      },
    },
    messages: {
      login_email: {
        remote: "Email already registered",
      },
      confirm_password: {
        equalTo: "Password and confirm password doesn't match",
      },
    },
  });

  $("#changePassword").validate({
    rules: {
      password: {
        minlength: 3,
      },
      confirm_password: {
        minlength: 3,
        equalTo: "#password",
      },
    },
    messages: {
      confirm_password: {
        equalTo: "Password and confirm password doesn't match",
      },
    },
  });

  $("#regForm").validate({
    rules: {
      email: {
        email: true,
        remote: {
          url: "is-user-email-exist",
          type: "get",
        },
      },
      password: {
        minlength: 3,
      },
      confirm_password: {
        minlength: 3,
        equalTo: "#password",
      },
    },
    messages: {
      email: {
        remote: "Email already registered",
      },
      confirm_password: {
        equalTo: "Password and confirm password doesn't match",
      },
    },
  });
});
