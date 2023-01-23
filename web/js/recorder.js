
// establish scope
var sttTimerRef;
var sttStartTime = new Date();

var ttsTimerRef;
var ttsStartTime = new Date();

var audioPlayer = new Audio();

// permission to use the mic
let audioIN = { audio: true };

navigator.mediaDevices.getUserMedia(audioIN)
.then(function (mediaStreamObj) {
	// 'then()' method returns a Promise

	// Connect mediastream to record audio element
	let recordAudio = document.getElementById('audioRecord');
	if ("srcObject" in recordAudio) {
		// srcObject is supported in the newer browsers
		recordAudio.srcObject = mediaStreamObj;
	}
	else { // older browsers
		recordAudio.src = window.URL.createObjectURL(mediaStreamObj);
	}

	// Start record
	let start = document.getElementById('btnStart');

	// This is the main thing to recorded
	// the audio 'MediaRecorder' API
        const options = {
                      audioBitsPerSecond: 16000,
                      audioBitrateMode: "constant",
                      mimeType: "audio/wav",
                      };
	let mediaRecorder = new MediaRecorder(mediaStreamObj);

	// Start event
	start.addEventListener('click', function (ev) {
		//console.log(mediaRecorder.state);
		if (mediaRecorder.state == 'recording'){
		    mediaRecorder.stop();
		    this.style.backgroundColor="lightGray";
		    this.innerHTML="Start Recording";
		} else {
		    mediaRecorder.start();
		    this.style.backgroundColor="red";
		    this.innerHTML="Stop Recording";
		}
	})

	// audio data available so push on chunk array
	mediaRecorder.ondataavailable = function (ev) {
		dataArray.push(ev.data);
	}

	// Chunk array to store the audio data
	let dataArray = [];

	// Convert the audio data in to blob
	// after stopping the recording
	mediaRecorder.onstop = function (ev) {
		// blob of type wav
		let audioData = new Blob(dataArray, { 'type': 'audio/wav;' });
		
		// clear the chunk array
		dataArray = [];

		// Creating audio url with reference
		// of created blob named 'audioData'
                sttStartTime = new Date();
		let audioSrc = window.URL.createObjectURL(audioData);
		createDownloadLink(audioData);
	}
})
.catch(function (err) {
	// caught an error
	//console.log(err.name, err.message);
	let x = 0;
});


function createDownloadLink(blob) 
{
    var url = URL.createObjectURL(blob);
    var au = document.createElement('audio');
    var li = document.createElement('li');
    var link = document.createElement('a');
    // add controls to the <audio> element 
    au.controls = true;
    au.src = url;

    // link the a element to the blob 
    link.href = url;
    link.download = new Date().toISOString() + '.wav';

    // add the new audio and a elements to the li element 
    li.appendChild(au);
    li.appendChild(link);

    // create upload file link
    var filename = 'new_junk.wav';
    var upload = document.createElement('a');
    upload.href = "#";

    // handle upload file button event
    upload.addEventListener("click", function(event) {
      var xhr = new XMLHttpRequest();
      xhr.onload = function(e) {
        if (this.readyState === 4) {
	  let serverResponse = e.target.responseText;
          //console.log("Server returned: ", e.target.responseText);
		
          // this is an odd pain in the arse
          serverResponse = serverResponse.substring(2,serverResponse.length -4);

	  document.getElementById('theResult').innerHTML = serverResponse;
          let sttEndTime = new Date();
	  let timeDelta = sttEndTime - sttStartTime;
	  document.getElementById("stt_timer").innerHTML=timeDelta;
        }
      };

      var fd = new FormData();
      fd.append("file", blob, filename);
      fd.append("quality", document.getElementById('quality').value);
      let lang = document.getElementById('lang').value;
      if (lang.length > 0)fd.append('language',lang);
      xhr.open("POST", "https://privox.io/cgi-bin/rectest.py", true);
      xhr.send(fd);
    })
    li.appendChild(document.createTextNode(" Listen ")); 	// add a space in between 
    li.appendChild(upload);					// add the upload link to li

    document.getElementById("stt_timer").innerHTML="Thinking ...";
    var recordingsList = document.getElementById('recordingsList');
    recordingsList.appendChild(li);
    upload.click();
}

function post_text(text)
{
    ttsStartTime = new Date();
    var xhr = new XMLHttpRequest();
    xhr.onload = function(e) {
      if (this.readyState === 4) {
        let serverResponse = e.target.responseText;
        let ttsEndTime = new Date();
        let timeDelta = ttsEndTime - ttsStartTime;
        document.getElementById("tts_timer").innerHTML=timeDelta;
        //document.getElementById("tts_timer").innerHTML=serverResponse;
	audioPlayer.setAttribute('src',serverResponse);
	audioPlayer.load();
	audioPlayer.play();
      }
    };

    var fd = new FormData();
    fd.append("text", text);
    let voice = 'voice1';
    if (document.getElementById('fvoice2').checked)voice='voice2';
    //console.log("voice=" + voice + " text=" + text);
    document.getElementById("tts_timer").innerHTML="Thinking ...";
    fd.append("voice", voice);
    xhr.open("POST", "https://privox.io/cgi-bin/playtest.py", true);
    xhr.send(fd);
}

