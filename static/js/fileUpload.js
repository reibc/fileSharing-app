// // Get the file input element
// let inputForm = document.getElementById('file-to-save')
// // Get the upload button element
// let uploadButton = document.getElementById('upload_button');
// // A list of the selected files
// let selected_files = []
// uploadButton.addEventListener('click', (event) => {
//     event.preventDefault()
//     var files = inputForm.files;
//     if (files.length >0){
//         let formData = new FormData()
//         formData.append('action', 'upload')
//         for (let i = 0; i < files.length; i++){
//             var file = files[i];
//             selected_files.push(file)
//             if(file.size > 100000000){
//                 alert('File is too large')
//                 eturn;
//             }
//         }
//         selected_files.forEach((file) => {
//             formData.append('file', file)
//         })
//         fetch('http://127.0.0.1:5000/', {
//             method: 'POST',
//             body: formData
//         })
//         .then(() => {
//             location.reload()
//         })
//         .catch(error => alert(error))
//     } else {
//     alert('No files selected');
//     }
// })