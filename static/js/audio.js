
let audioContext = new (window.AudioContext || window.webkitAudioContext)();
const bufferSize = 4096;

let currentAudioPlayer;
let isAudioPlaying = false; 
let analyser = null; 
let source = null; 
let isAnalyzing = false; 
let currentPlayer; 
let youtubeIds = ['PB4VaN_qV3Q', 'Qp3b-RXtz4w'] // 27vwjrbKFZo
let youtubeIndex = 0;


let isInitializedAudio;




document.addEventListener('DOMContentLoaded', function () {
    microphoneButton = getId("microphone-button");
    earphoneButton = getId("earphone-button");

    initializeMp3Yt();
    //initializeMusic();

});

socket.on('incoming_audio', async data => {

    if (data && data.byteLength > 0) {
        try {
            const arrayBuffer = convertToArrayBuffer(data);
            const decodedData = await decodeAudioDataAsync(arrayBuffer);
            if (decodedData) {
                playAudioBuffer(decodedData);
            } else {
                console.log('Decoded audio data is empty or invalid');
            }
        } catch (error) {
            console.log('Error decoding audio data:');

        }
    } else {
        console.log('Received silent or invalid audio data');
    }
});

function convertToArrayBuffer(data) {
    if (data instanceof ArrayBuffer) {
        return data;
    } else if (data.buffer instanceof ArrayBuffer) {
        return data.buffer;
    } else {
        throw new Error('Unsupported data format');
    }
}

function decodeAudioDataAsync(arrayBuffer) {
    try {

    }
    catch(error) {
        return new Promise((resolve, reject) => {
            audioContext.decodeAudioData(arrayBuffer, resolve, reject);
        });

    }
}

function playAudioBuffer(audioBuffer) {
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start(0);
}




function enableBorderMovement() {
    if (isAudioPlaying && currentAudioPlayer) {
        if (!isAnalyzing) {
            startAudioAnalysis(); 
        }
    }
}

function getSelfFromUserList() {
    const userProfiles = userList.querySelectorAll('.profile-container');
    if (!userList || !userProfiles.length) return null; 
    for (const profile of userProfiles) {
        if (profile.id === currentUserId) {
            return profile.querySelector('.profile-pic');
        }
    }
    return null; // Return null if no profile found
}


function stopAudioAnalysis() {
    if (!isAnalyzing) return;

    isAnalyzing = false;

    let selfProfileDisplayElementList = getSelfFromUserList();
    if(selfProfileDisplayElementList) {
        selfProfileDisplayElementList.style.borderRadius = '50%';
        
    }
    


    const profileDisplayElement = document.getElementById('profile-display');
    const selfProfileDisplayElement = document.getElementById('self-profile-image');
    
    resetWiggleEffect(profileDisplayElement, selfProfileDisplayElement,selfProfileDisplayElementList);
}


async function playAudio(audioUrl) {
    try {
        if (currentPlayer) {
            currentPlayer.pause(); 
            currentPlayer.remove();
        }

        const audioElement = document.createElement('audio');
        currentAudioPlayer = audioElement;
        audioElement.id = 'audio-player';
        audioElement.src = audioUrl;
        audioElement.controls = true; 
        document.body.appendChild(audioElement);

        currentPlayer = audioElement;

        audioElement.addEventListener('play', function() {
            if (isParty) {
                enableBorderMovement();
            }
            startAudioAnalysis();
        });

        audioElement.addEventListener('ended', function() {
            stopCurrentMusic();
            isAnalyzing = false;
            if (analyser) {
                analyser.disconnect();
            }
        });

        await audioElement.play();
        isAudioPlaying = true;

    } catch (error) {
        console.error("Error playing audio:", error);
    }
}

function startAudioAnalysis() {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();

    if (!(currentPlayer instanceof HTMLMediaElement)) {
        console.error('currentPlayer is not a valid HTMLMediaElement.');
        return;
    }

    analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaElementSource(currentPlayer);
    source.connect(analyser);
    analyser.connect(audioContext.destination);

    isAnalyzing = true;

    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    let recentVolumes = [];
    const bufferSize = 10;

    analyzeAudio(bufferSize, dataArray, recentVolumes); 
}

function analyzeAudio(bufferSize, dataArray, recentVolumes) {
    if (!isAnalyzing || !analyser) return; 

    analyser.getByteFrequencyData(dataArray);

    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
    }

    const averageVolume = sum / dataArray.length;

    recentVolumes.push(averageVolume);
    if (recentVolumes.length > bufferSize) {
        recentVolumes.shift();
    }

    const dynamicThreshold = recentVolumes.reduce((acc, val) => acc + val, 0) / recentVolumes.length;

    const scaleFactor = 1 + (averageVolume / 128); 
    const borderColor = `rgb(${Math.min(255, averageVolume * 2)}, 0, ${Math.max(0, 255 - averageVolume * 2)})`;

    const profileDisplayElement = document.getElementById('profile-display');
    const selfProfileDisplayElement = document.getElementById('self-profile-image');

    if (averageVolume > dynamicThreshold) {
        if (profileDisplayElement) {
            profileDisplayElement.classList.add('dancing-border');
            profileDisplayElement.style.transform = `scale(${scaleFactor})`;
            profileDisplayElement.style.borderColor = borderColor;
        }
        if (selfProfileDisplayElement) {
            selfProfileDisplayElement.classList.add('dancing-border');
            selfProfileDisplayElement.style.transform = `scale(${scaleFactor})`;
            selfProfileDisplayElement.style.borderColor = borderColor;
        }

        const selfUserListProfileList = getSelfFromUserList()
        if(selfUserListProfileList) {
            selfUserListProfileList.classList.add('dancing-border');
            selfUserListProfileList.style.transform = `scale(${scaleFactor})`;
            selfUserListProfileList.style.borderColor = borderColor;
        }
    } else {
        resetStyles(profileDisplayElement, selfProfileDisplayElement);
    }

    requestAnimationFrame(() => analyzeAudio(bufferSize, dataArray, recentVolumes));
}

function resetStyles(profileDisplayElement, selfProfileDisplayElement) {
    if (profileDisplayElement) {
        profileDisplayElement.classList.remove('dancing-border');
        profileDisplayElement.style.transform = `scale(1)`;
        profileDisplayElement.style.borderColor = 'rgb(17, 18, 20)';
    }
    if (selfProfileDisplayElement) {
        selfProfileDisplayElement.classList.remove('dancing-border');
        selfProfileDisplayElement.style.transform = `scale(1)`;
        selfProfileDisplayElement.style.borderColor = 'rgb(17, 18, 20)';
    }
    const selfUserListProfileList = getSelfFromUserList();
    if(selfUserListProfileList) {
        selfUserListProfileList.classList.remove('dancing-border');
        selfUserListProfileList.style.transform = `scale(1)`;
        selfUserListProfileList.style.borderColor = 'rgb(17, 18, 20)';
    }
}

function stopCurrentMusic() {
    if (currentAudioPlayer) {
        currentAudioPlayer.pause(); 
        currentAudioPlayer.currentTime = 0; 
        isAudioPlaying = false; 
        
        resetProfileBorders(); 

        if (source) {
            source.disconnect();
            source = null;
        }
        if (analyser) {
            analyser.disconnect();
            analyser = null; 
        }

        isAnalyzing = false;
    }
}

function resetProfileBorders() {
    const profileDisplayElement = document.getElementById('profile-display');
    const selfProfileDisplayElement = document.getElementById('self-profile-image');


    const selfProfileDisplayElementList = getSelfFromUserList();
    if(selfProfileDisplayElementList) {
        selfProfileDisplayElementList.style.borderRadius = '50%';
        selfProfileDisplayElementList.style.borderColor = '';
        selfProfileDisplayElementList.style.transform = '';
    }

    if (profileDisplayElement) {
        profileDisplayElement.style.borderRadius = '50%';
        profileDisplayElement.style.borderColor = '';
        profileDisplayElement.style.transform = '';
    }
    if (selfProfileDisplayElement) {
        selfProfileDisplayElement.style.borderRadius = '50%';
        selfProfileDisplayElement.style.borderColor = '';
        selfProfileDisplayElement.style.transform = '';
    }
}





function initializeMp3Yt() {
    const modal = createEl('div', { className: 'modal' });
    document.body.appendChild(modal);

    const handleClick = async function () {
        if (isAudioPlaying || isInitializedAudio) {
            return; 
        }

        const ytId = youtubeIds[youtubeIndex];
        document.removeEventListener('click', handleClick);
        modal.remove(); 

        isAudioPlaying = true;
        isInitializedAudio = true;

        const audioStream = await fetchAudioStream(ytId);
        if (audioStream) {
            playAudioFromStream(audioStream);
        } else {
            console.error('Failed to retrieve audio stream.');
        }
    };

    document.addEventListener('click', handleClick);
}
async function fetchAudioStream(videoId) {
    try {
        const response = await fetch(`http://localhost:5009?videoId=${encodeURIComponent(videoId)}`);
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        return response.body;
    } catch (error) {
        console.error('Error fetching audio stream:', error);
        return null;
    }
}

async function playAudioFromStream(audioStream) {
    if (!audioStream) {
        console.error('No audio stream provided');
        return;
    }

    const mediaSource = new MediaSource();
    const audio = new Audio();
    currentAudioPlayer = audio;

    mediaSource.addEventListener('sourceopen', async () => {
        const sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
        const reader = audioStream.getReader();
        setTimeout(() => {
            enableBorderMovement();
        }, 100);

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                mediaSource.endOfStream();
                break;
            }
            await new Promise(resolve => {
                sourceBuffer.addEventListener('updateend', resolve, { once: true });
                sourceBuffer.appendBuffer(value);
                
            });
        }
    });

    audio.src = URL.createObjectURL(mediaSource);
    audio.play().catch(error => {
        console.error('Error playing audio:', error);
    });

    audio.addEventListener('ended', () => {
        URL.revokeObjectURL(audio.src);
    });
}





function activateSoundOutput() {
    async function requestSoundOutputPermissions() {
        try {
            await navigator.mediaDevices.getUserMedia({ audio: false, video: true });
            return true; 
        } catch (error) {
            return false;
        }
    }

    function getSoundOutputList() {
        return navigator.mediaDevices.enumerateDevices()
            .then(devices => devices.filter(device => device.kind === 'audiooutput'));
    }

    async function updateSoundOutputOptions() {
        const dropdown = getId('sound-output-dropdown');
        dropdown.innerHTML = ''; 

        try {
            const hasPermission = await requestSoundOutputPermissions();

            if (hasPermission) {
                const soundOutputs = await getSoundOutputList();
                soundOutputs.forEach((output, index) => {
                    const option = createEl('option');
                    option.style.fontSize = '12px';
                    option.style.border = 'none';
                    option.value = output.deviceId;
                    option.textContent = output.label || `Sound Output ${index + 1}`;
                    dropdown.appendChild(option);
                });
            }

            const defaultOption = createEl('option');
            defaultOption.style.fontSize = '12px';
            defaultOption.value = 'default';
            defaultOption.textContent = 'Default Sound Output';
            dropdown.appendChild(defaultOption);

        } catch (error) {
            console.error('Error updating sound output options:', error);

            const defaultOption = createEl('option');
            defaultOption.style.fontSize = '12px';
            defaultOption.value = 'default';
            defaultOption.textContent = 'Default Sound Output';
            dropdown.appendChild(defaultOption);
        }
    }

    updateSoundOutputOptions();
    navigator.mediaDevices.addEventListener('devicechange', updateSoundOutputOptions);
}



  

let isMicrophoneOpen = true;
function setMicrophone() {
    let imagePath = isMicrophoneOpen ? `/static/images/icons/whitemic.png` : `/static/images/icons/redmic.png`;
    microphoneButton.src = imagePath;
    isMicrophoneOpen = !isMicrophoneOpen;
    console.log("Set microphone! to " , isMicrophoneOpen);
}

let isEarphonesOpen = true;
function setEarphones() {
    let imagePath = isEarphonesOpen ? `/static/images/icons/whiteearphones.png` : `/static/images/icons/redearphones.png`;
    earphoneButton.src = imagePath;
    isEarphonesOpen = !isEarphonesOpen;
    console.log("Set earphones! to " , isEarphonesOpen);
}



async function activateMicAndSoundOutput() {
    activateMicAndCamera();
    activateSoundOutput();
}
async function sendAudioData() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = async (e) => {

        };

        mediaRecorder.start();

    } catch (err) {
        console.error('Error accessing microphone:', err);
    }
}


function activateMicAndCamera() {
    async function requestMediaPermissions() {
        try {
            await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
            return true; // Permission granted
        } catch (error) {
            return false; // Permission denied or error occurred
        }
    }

    function getMediaDevicesList() {
        return navigator.mediaDevices.enumerateDevices()
            .then(devices => devices.filter(device => device.kind === 'audioinput' || device.kind === 'videoinput'));
    }
    async function updateMediaOptions() {
        const micDropdown = getId('sound-mic-dropdown');
        micDropdown.innerHTML = ''; // Clear existing options
        const cameraDropdown = getId('camera-dropdown');
        cameraDropdown.innerHTML = ''; // Clear existing options
        try {
            const hasPermission = await requestMediaPermissions();

            if (hasPermission) {
                const mediaDevices = await getMediaDevicesList();
                mediaDevices.forEach((device, index) => {
                    const option = createEl('option',{fontSize:'12px',border:'none'});

                    option.value = device.deviceId;
                    if (device.kind === 'audioinput') {
                        option.textContent = device.label || `Microphone ${index + 1}`;
                        micDropdown.appendChild(option);
                    } else if (device.kind === 'videoinput') {
                        option.textContent = device.label || `Camera ${index + 1}`;
                        cameraDropdown.appendChild(option);
                    }
                });
            }

            // Add default microphone and camera options at the end
            const defaultMicOption = createEl('option',{fontSize:'12px',value:'default'});
            defaultMicOption.textContent = 'Default Microphone';
            micDropdown.appendChild(defaultMicOption);

            const defaultCameraOption = createEl('option',{fontSize:'12px',value:'default'});
            defaultCameraOption.textContent = 'Default Camera';
            cameraDropdown.appendChild(defaultCameraOption);

        } catch (error) {
            console.error('Error updating media options:', error);

            // Ensure the default options are added even if an error occurs
            const defaultMicOption = createEl('option',{fontSize:'12px',value:'default'});
            defaultMicOption.textContent = 'Default Microphone';
            micDropdown.appendChild(defaultMicOption);

            const defaultCameraOption = createEl('option',{fontSize:'12px',value:'default'});
            defaultCameraOption.textContent = 'Default Camera';
            cameraDropdown.appendChild(defaultCameraOption);
        }
    }

    updateMediaOptions();
    if(navigator && navigator.mediaDevices) {
        navigator.mediaDevices.addEventListener('devicechange', updateMediaOptions);
    }
}



function closeCurrentCall() {
    currentAudioPlayer = getId('audio-player');
    playAudio('/static/sounds/leavevoice.mp3');

    const sp = getId('sound-panel');
    const oldVoiceId = currentVoiceChannelId;
    sp.style.display = 'none';
    clearVoiceChannel(oldVoiceId);
    currentVoiceChannelId = '';
    currentVoiceChannelGuild = '';
    const buttonContainer = channelsUl.querySelector(`li[id="${oldVoiceId}"]`);

    mouseLeaveChannelButton(buttonContainer, false,oldVoiceId);
    usersInVoice[oldVoiceId] = [];

    const data = {
        'guild_id' : currentVoiceChannelGuild,
        'channel_id' : currentVoiceChannelId
    }
    socket.emit('leave_voice_channel',data)
}
function clearVoiceChannel(channel_id) {
    const channelButton = channelsUl.querySelector(`li[id="${channel_id}"]`);
    if(!channelButton) {return; }
    const buttons = channelButton.querySelectorAll('.channel-button');
    buttons.forEach((btn,index) => {
        btn.remove();
    });
    let channelUsersContainer = channelButton.querySelector('.channel-users-container');
    if(channelUsersContainer) {
        channelUsersContainer.remove();
    }
    let existingContentWrapper = channelButton.querySelector('.content-wrapper');
    console.log(existingContentWrapper.style.marginRight);
    existingContentWrapper.style.marginRight = '100px';
}


let cachedAudioNotify = null;

function playNotification() {
    try {
        if (!cachedAudioNotify) {
            cachedAudioNotify = new Audio("https://raw.githubusercontent.com/TheLp281/LiventCord/main/notification.mp3");
        }
        cachedAudioNotify.play();
    } catch (error) {
        console.log(error);
    }
}


function initializeMusic() {
    const modal = createEl('div', { className: 'modal'});
    document.body.appendChild(modal);

    const songs = [
        '/static/sounds/musics/2.mp3',
        '/static/sounds/musics/1.mp3',
        '/static/sounds/musics/3.mp3',
        '/static/sounds/musics/4.mp3'
    ];

    let currentSongIndex = 0;

    function playCurrentSong() {
        const currentSong = songs[currentSongIndex];
        
        playAudio(currentSong); 
        
        const audio = new Audio(currentSong);
        audio.onended = function () {
            currentSongIndex++;
            if (currentSongIndex >= songs.length) {
                currentSongIndex = 0;
            }

            playCurrentSong(); 
        };
    }

    modal.addEventListener('click', function () {
        playCurrentSong();
        modal.style.display = 'none'; 
    });
}
