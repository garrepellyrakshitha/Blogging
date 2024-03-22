// post data
function post(path, params, method='post') {
  // The rest of this code assumes you are not using a library.
  // It can be made less verbose if you use one.
  const form = document.createElement('form');
  form.method = method;
  form.action = path;

  for (const key in params) {
    if (params.hasOwnProperty(key)) {
      const hiddenField = document.createElement('input');
      hiddenField.type = 'hidden';
      hiddenField.name = key;
      hiddenField.value = params[key];

      form.appendChild(hiddenField);
    }
  }

  document.body.appendChild(form);
  form.submit();
}

function getCityId(city) {
  var id = $('#cityList option').filter(function () {
    return this.value == city;
  }).data('city-id');
  $("#cityId").val(id)
}

function incrementValue()
{
    let value = parseInt(document.getElementById('quantityInp').value, 10);
    value = isNaN(value) ? 0 : value;
    value++;
    if(value > 1){
      $("#btn-decr").removeAttr("disabled")
    }
    document.getElementById('quantityInp').value = value;
    $('#quantityInp').bind('input propertychange', function() {
      console.log($(this).val());
   });
}

function decrementValue()
{
    let value = parseInt(document.getElementById('quantityInp').value, 10);
    value = isNaN(value) ? 0 : value;
    value--;
    if(value == 1){
      $("#btn-decr").attr("disabled","diabled")
    }
    document.getElementById('quantityInp').value = value;
    
    $('#quantityInp').trigger("#quantityInp");
   
}
