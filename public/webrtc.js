// Use Google's public STUN server
const iceConfig = {
    'iceServers': [{'urls': ['stun:stun2.1.google.com:19302']}]
};

// create a WebRTC connection object
let webRTCConnection = new RTCPeerConnection(iceConfig);

function processMessageAsWebRTC(message, messageType) {
    switch (messageType) {
        case 'webRTC-offer':
            void webRTCConnection.setRemoteDescription(new RTCSessionDescription(message.offer));
            webRTCConnection.createAnswer().then(answer => {
                void webRTCConnection.setLocalDescription(answer);
                socket.send(JSON.stringify({'messageType': 'webRTC-answer', 'answer': answer}));
            });
            break;
        case 'webRTC-answer':
            void webRTCConnection.setRemoteDescription(new RTCSessionDescription(message.answer));
            break;
        case 'webRTC-candidate':
            void webRTCConnection.addIceCandidate(new RTCIceCandidate(message.candidate));
            break;
        default:
            console.log("received an invalid WS messageType");
    }
}

function startVideo() {
    const constraints = {video: true, audio: true};
    navigator.mediaDevices.getUserMedia(constraints).then((myStream) => {
        const elem = document.getElementById("myVideo");
        elem.srcObject = myStream;

        // add your local stream to the connection
        myStream.getTracks().forEach(track => webRTCConnection.addTrack(track, myStream));

        // when a remote stream is added, display it on the page
        webRTCConnection.ontrack = function (event) {
            const remoteVideo = document.getElementById('otherVideo');
            remoteVideo.srcObject = event.streams[0];
        };

        // called when an ice candidate needs to be sent to the peer
        webRTCConnection.onicecandidate = function (event) {
            if (event.candidate) {
                socket.send(JSON.stringify({'messageType': 'webRTC-candidate', 'candidate': event.candidate}));
            }
        };
    });
}

function connectWebRTC() {
    // create and send an offer
    webRTCConnection.createOffer().then(webRTCOffer => {
        socket.send(JSON.stringify({'messageType': 'webRTC-offer', 'offer': webRTCOffer}));
        void webRTCConnection.setLocalDescription(webRTCOffer);
    });
}
