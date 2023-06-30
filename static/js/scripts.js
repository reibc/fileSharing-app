let textArea = document.getElementById("textarea");
let element = document.querySelector('.menu')

const fileInput = document.getElementById('file-to-save');
const fileDetails = document.getElementById('file-details');
const downloadButton = document.querySelector('.receiveForm button');
let inputButton = document.getElementById('upload_button')
let fileList = document.getElementById('list-elements')
let uploadButton = document.getElementById('upload-link');
let selectedFiles = []

function convertor(size){
  original_size = size
  size = size / (1024*1024)
  if(size > 1 && size < 1000){
    return `${size.toFixed(1)} MB`
  }
  if(size > 1000){
    return `${(size/1024).toFixed(1)} GB `
  }
  return `${original_size} B`
}

let li = ``
let i = 0

function checkIfInArray(file){
  return selectedFiles.some(selected => {
    if(selected.name.includes(file)){
      return true
    }
    return false
  })
}

fileInput.addEventListener('change', () => {
  uploadIcon = document.getElementById('upload-icon')
  fileName = document.getElementsByClassName('file-name')
  let files = [...fileInput.files]
  if(files.length > 0){
    inputButton.style.removeProperty("display");
    files.forEach((file) => {
      if(!checkIfInArray(file.name)){
        if(file.size > 100000000){
          alert('File is too large')
          file.length === undefined ? inputButton.style = 'display: none;' : console.log(`File length = ${file.length}`)
          return;
        }
        selectedFiles.push(file)
        let size = convertor(file.size)
        uploadIcon.style = 'display: none;'
        li = li + `<li id="selected-file-${i}">
          <div class="file-name" id="file-name">${file.name}</div>
          <div class="file-size">${size}</div>
          <div class="file-cancel ${i}">X</div>
        </li>`
        fileList.innerHTML = li
        i +=1
      }

    })
  }
  removeElementOnClick(uploadIcon, inputButton)
  try{
    addEvent()
  }catch(error){
    console.log(`File size is too large`)
  }
  
})

function addEvent(){
  document.getElementById("file-name").addEventListener("click", function() {
    document.querySelector("#file-to-save").click();
  });
}
let cleanInput = true
function removeElementOnClick(uploadIcon, inputButton){
  let deleteFile = document.querySelectorAll(`.file-cancel`)
  let listElement = fileList.getElementsByTagName('li')
  let index = null
  var files = [...fileInput.files]
  console.log(selectedFiles)
  for( element of deleteFile){
    element.addEventListener('click', (event) => {
      index = event.target.className.split(" ")[1]
      let fileElement = document.getElementById(`selected-file-${index}`)
      let fileName = fileElement.querySelector(`#file-name`)
      console.log(selectedFiles)
      console.log(fileName.innerHTML)
      const checkFile = function(file){
        return selectedFiles.findIndex(selected => selected.name.includes(file))
      }
      result = checkFile(fileName.innerHTML)
      result != -1 ? selectedFiles.splice(result, 1) : console.log(`File not found`)
      console.log(`after =>`)
      console.log(selectedFiles)
      files[index] = []
      files = files.filter(file => file.length > 0)
      fileElement.remove()
      li = fileList.innerHTML
      if(listElement.length == 0){
        inputButton.style = "display : none;"
        uploadIcon.style.removeProperty('display')
      }
    })
  }
}

uploadButton.addEventListener('click', (event) => {
    event.preventDefault()
    var files = fileInput.files;
    var accessLevel = document.getElementById('access')
    var accessValue = accessLevel.value;
    var expirationTime = document.getElementById('expiration-time')
    var expirationValue = expirationTime.value;
    console.log(`${accessValue} => ${expirationValue}`)
    if (files.length >0){
        let formData = new FormData()
        formData.append('action', 'upload')
        formData.append('accessLevel', accessValue)
        formData.append('expirationTime', expirationValue)
        // for (let i = 0; i < files.length; i++){
        //     var file = files[i];
        //     selectedFiles.push(file)
        //     if(file.size > 100000000){
        //         alert('File is too large')
        //         eturn;
        //     }
        // }
        selectedFiles.forEach((file) => {
            formData.append('file', file)
        })
        fetch('http://127.0.0.1:5000/', {
            method: 'POST',
            body: formData
        })
        .then(() => {
          fileList.style = "display: none;"
          inputButton.style = "display: none;"
          $('.cd-popup').removeClass('is-visible');
          let generatedCode = document.getElementById('generated-code')
          fetch('http://127.0.0.1:5000/get_code')
          .then(response => response.json())
          .then(data => {
            let code = data.code
            console.log(code)
            generatedCode.innerHTML = `<div id="code-id">${code}</div>`
          })
        })
        .catch(error => alert(error))
    } else {
    alert('No files selected');
    }
})




textArea.addEventListener("focus", function(event){
  event.target.style.border = "1px solid #ADB5BD"
  
});

textArea.addEventListener("blur", function(event){
  event.target.style.border = ""
});

function toggleMenu() {
  const toggleMenu = document.querySelector('.menu');
  toggleMenu.classList.toggle('active');
}

document.addEventListener("click", function(event) {
  if (!event.target.closest('.action')) {
    const toggleMenu = document.querySelector('.menu');
    toggleMenu.classList.remove('active');
  }
});

function uploadFile() {
  const form = document.querySelector('form');
  form.submit();
};

// Disable the downloadButton if the input box is empty
// downloadButton.disabled = true;
// textarea.addEventListener('input', function() {
//   if (textarea.value.trim() !== '') {
//     downloadButton.disabled = false;
//   } else {
//     downloadButton.disabled = true;
//   }
// });


// function openUrl(){
//   var url = document.getElementById("textarea").value;
//   window.open(url);
// }

// var submitBtn = document.getElementById("downloadButton");
// submitBtn.addEventListener("click", openUrl);

var deleteBtn = document.getElementById("deleteButton")

