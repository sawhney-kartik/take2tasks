let mediaRecorder;
let audioChunks = [];

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.start();
            document.getElementById('status').textContent = 'Recording...';
            document.querySelector('button[onclick="stopRecording()"]').disabled = false;

            mediaRecorder.addEventListener('dataavailable', event => {
                audioChunks.push(event.data);
            });

            mediaRecorder.addEventListener('stop', () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
                const formData = new FormData();
                formData.append('file', audioBlob, 'take2.mp3');

                fetch('/upload-audio', {
                    method: 'POST',
                    body: formData,
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Success:', data);
                    document.getElementById('status').textContent = 'File uploaded and processed!';
                })
                .catch((error) => {
                    console.error('Error:', error);
                    document.getElementById('status').textContent = 'Error uploading file!';
                });

                audioChunks = [];
            });

            mediaRecorder.addEventListener('error', error => console.error('Error recording audio:', error));
        })
        .catch(error => console.error('Error accessing media devices:', error));
}

function stopRecording() {
    mediaRecorder.stop();
    document.getElementById('status').textContent = 'Stopping...';
    document.querySelector('button[onclick="stopRecording()"]').disabled = true;
}
