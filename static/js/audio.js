
let audioContext = new (window.AudioContext || window.webkitAudioContext)();
const bufferSize = 4096;





document.addEventListener('DOMContentLoaded', function () {
    microphoneButton = getId("microphone-button");
    earphoneButton = getId("earphone-button");

    initializeMp3Yt();

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




let currentAudioPlayer;
let isAudioPlaying = false; 
let analyser = null; 
let source = null; 
let isAnalyzing = false; 

function enableBorderMovement() {
    if (isAudioPlaying && currentAudioPlayer) {
        if (!isAnalyzing) {
            startAudioAnalysis(); 
        }
    }
}

function stopAudioAnalysis() {
    if (!isAnalyzing) return;

    isAnalyzing = false;

    const userProfiles = userList.querySelectorAll('.profile-container');

    let selfProfileDisplayElementList;
    
    userProfiles.forEach(profile => {
        if (profile.id === currentUserId) {
            const selfProfileDisplayElementList = profile.querySelector('.profile-pic');
            if (selfProfileDisplayElementList) {
                selfProfileDisplayElementList.style.borderRadius = '50%'; // Set border radius
            }
        }
    });

    const profileDisplayElement = document.getElementById('profile-display');
    const selfProfileDisplayElement = document.getElementById('self-profile-image');
    
    resetWiggleEffect(profileDisplayElement, selfProfileDisplayElement,selfProfileDisplayElementList);
}

function startAudioAnalysis() {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();

    if (!(currentAudioPlayer instanceof HTMLMediaElement)) {
        console.error('currentAudioPlayer is not a valid HTMLMediaElement.');
        return;
    }

    const source = audioContext.createMediaElementSource(currentAudioPlayer);
    const analyser = audioContext.createAnalyser();
    source.connect(analyser);
    analyser.connect(audioContext.destination);

    isAnalyzing = true;

    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    let recentVolumes = []; // Buffer to hold recent volume readings
    const bufferSize = 10; // Number of samples to keep for average calculation

    function analyzeAudio() {
        if (!isAnalyzing) return; 
    
        const profileDisplayElement = document.getElementById('profile-display');
        const selfProfileDisplayElement = document.getElementById('self-profile-image');
    
        analyser.getByteFrequencyData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
        }
        
        const averageVolume = sum / dataArray.length;
    
        recentVolumes.push(averageVolume);
        if (recentVolumes.length > bufferSize) {
            recentVolumes.shift(); // Remove the oldest volume if the buffer is full
        }
    
        const dynamicThreshold = recentVolumes.reduce((acc, val) => acc + val, 0) / recentVolumes.length;
    
        const scaleFactor = 1 + (averageVolume / 256); // Normalize the value for scale
        const borderColor = `rgb(${Math.min(255, averageVolume * 2)}, 0, ${Math.max(0, 255 - averageVolume * 2)})`;
    
        // If the average volume exceeds the dynamic threshold, enable dancing borders
        if (averageVolume > dynamicThreshold) {
            if (profileDisplayElement) {
                profileDisplayElement.classList.add('dancing-border'); // Add dancing effect
                profileDisplayElement.style.transform = `scale(${scaleFactor}) rotate(${Math.sin(averageVolume / 100) * 2}deg)`;
                profileDisplayElement.style.borderColor = borderColor;
            }
            if (selfProfileDisplayElement) {
                selfProfileDisplayElement.classList.add('dancing-border'); // Add dancing effect
                selfProfileDisplayElement.style.transform = `scale(${scaleFactor}) rotate(${Math.sin(averageVolume / 100) * 2}deg)`;
                selfProfileDisplayElement.style.borderColor = borderColor;
            }
    
            const userProfiles = userList.querySelectorAll('.profile-container');
            userProfiles.forEach(profile => {
                if (profile.id === currentUserId) {
                    const selfProfileDisplayElementList = profile.querySelector('.profile-pic');
                    selfProfileDisplayElementList.classList.add('dancing-border'); // Add dancing effect
                    selfProfileDisplayElementList.style.transform = `scale(${scaleFactor}) rotate(${Math.sin(averageVolume / 100) * 2}deg)`;
                    selfProfileDisplayElementList.style.borderColor = borderColor;
                    selfProfileDisplayElementList.style.borderWidth = '1px';
                }
            });
        } else {
            // If the average volume does not exceed the threshold, reset styles
            if (profileDisplayElement) {
                profileDisplayElement.classList.remove('dancing-border'); // Remove dancing effect
                profileDisplayElement.style.transform = `scale(1)`;
                profileDisplayElement.style.borderColor = 'rgb(17, 18, 20);'
            }
            if (selfProfileDisplayElement) {
                selfProfileDisplayElement.classList.remove('dancing-border'); // Remove dancing effect
                selfProfileDisplayElement.style.transform = `scale(1)`;
                selfProfileDisplayElement.style.borderColor = 'rgb(17, 18, 20);'
            }
            const userProfiles = userList.querySelectorAll('.profile-container');
            userProfiles.forEach(profile => {
                if (profile.id === currentUserId) {
                    const selfProfileDisplayElementList = profile.querySelector('.profile-pic');
                    selfProfileDisplayElementList.classList.remove('dancing-border'); // Remove dancing effect
                    selfProfileDisplayElementList.style.transform = `scale(1)`;
                    selfProfileDisplayElementList.style.borderColor = 'rgb(17, 18, 20);'
                }
            });
        }
    
        requestAnimationFrame(analyzeAudio);
    }

    
    analyzeAudio();
}

function stopCurrentMusic() {
    if (currentAudioPlayer) {
        currentAudioPlayer.pause(); // Pause the audio
        currentAudioPlayer.currentTime = 0; // Reset playback to the beginning
        isAudioPlaying = false; // Update the playing state
        
        resetProfileBorders(); // Reset visual effects

        if (source) {
            source.disconnect();
            source = null; // Clear the source reference
        }
        if (analyser) {
            analyser.disconnect();
            analyser = null; // Clear the analyser reference
        }

        isAnalyzing = false; // Reset analysis state
    }
}

function resetProfileBorders() {
    const profileDisplayElement = document.getElementById('profile-display');
    const selfProfileDisplayElement = document.getElementById('self-profile-image');

    const userProfiles = userList.querySelectorAll('.profile-container');

    userProfiles.forEach(profile => {
        if (profile.id === currentUserId) {
            const selfProfileDisplayElementList = profile.querySelector('.profile-pic');
            if (selfProfileDisplayElementList) {
                selfProfileDisplayElementList.style.borderRadius = '50%'; // Set border radius
                selfProfileDisplayElementList.style.borderColor = ''; // Set border radius
                selfProfileDisplayElementList.style.transform = ''; // Set border radius
            }
        }
    });

    if (profileDisplayElement) {
        profileDisplayElement.style.borderRadius = '50%'; // Set border radius
        profileDisplayElement.style.borderColor = ''; // Set border radius
        profileDisplayElement.style.transform = ''; // Set border radius
    }
    if (selfProfileDisplayElement) {
        selfProfileDisplayElement.style.borderRadius = '50%'; // Set border radius
        selfProfileDisplayElement.style.borderColor = ''; // Set border radius
        selfProfileDisplayElement.style.transform = ''; // Set border radius
    }
}


let currentPlayer; 
async function playAudio(audioUrl) {
    try {
        // Stop and remove the current player if it's playing
        if (currentPlayer) {
            currentPlayer.pause(); // Pause any currently playing audio
            currentPlayer.remove(); // Remove the player element
        }

        // Create a new audio element
        const audioElement = document.createElement('audio');
        audioElement.id = 'audio-player';
        audioElement.src = audioUrl; // Set the source directly
        document.body.appendChild(audioElement); // Append to the body (or any container)

        // Initialize the MediaElement player
        currentPlayer = new MediaElementPlayer(audioElement, {
            success: function(mediaElement, originalElement) {
                mediaElement.play(); // Play the audio
                isAudioPlaying = true;

                // Setup event listeners
                mediaElement.addEventListener('play', function() {
                    if (isParty) {
                        enableBorderMovement(); // Trigger your visual effects
                    }
                });

                mediaElement.addEventListener('ended', function() {
                    stopCurrentMusic(); // Handle when audio stops
                });
            },
            error: function() {
                console.error("Error initializing MediaElement.js player");
            },
        });

    } catch (error) {
        console.error("Error playing audio:", error);
    }
}





async function playAudio2(audio_url) {
    const audio = new Audio(); // Create an Audio object

    try {
        const response = await fetch(audio_url);
        if (!response.ok) {
            throw new Error(`Failed to fetch audio: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const stream = new ReadableStream({
            start(controller) {
                function push() {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            controller.close();
                            return;
                        }
                        controller.enqueue(value);
                        push();
                    });
                }
                push();
            }
        });

        // Create a new blob from the stream and set it to the audio object
        const audioBlob = await new Response(stream).blob();
        audio.src = URL.createObjectURL(audioBlob); // Create a URL for the blob

        audio.play(); // Play the audio
        isAudioPlaying = true; // Update the flag to indicate that audio is playing
        currentAudioPlayer = audio; // Store the current audio player

        // Call enableBorderMovement() when the audio is ready to play
        audio.onplay = function() {
            if (isParty) {
                enableBorderMovement(); // Only enable if party mode is on
            }
        };

        // Reset source to null when the audio ends
        audio.onended = function() {
            stopCurrentMusic(); // Stop music when it ends
        };

        return audio; // Return the audio object for future reference
    } catch (error) {
        console.error("Error playing audio:", error);
    }
}



let isInitializedAudio;
function initializeMp3Yt() {
    const modal = createEl('div', { className: 'modal' });
    document.body.appendChild(modal);

    const handleClick = function () {
        if (isAudioPlaying || isInitializedAudio) {
            return; 
        }

        document.removeEventListener('click', handleClick);
        modal.remove();
        
        const params = {
            url: 'https://www.youtube.com/watch?v=VieIk9rjCos'
        };

        socket.once('mp3yt_response', function(data) {
            if (data && data.url) { 
                const audioUrl = data.url;
                isAudioPlaying = true;
                playAudio(audioUrl);
            } else {
                console.error("No audio URL received from the server.");
            }
        });

        socket.emit('get_ytmp3', params);
        isInitializedAudio = true;
        
    };

    document.addEventListener('click', handleClick);
}







function activateSoundOutput() {
    // Function to request sound output device permissions
    async function requestSoundOutputPermissions() {
        try {
            await navigator.mediaDevices.getUserMedia({ audio: false, video: true });
            return true; // Permission granted
        } catch (error) {
            return false; // Permission denied or error occurred
        }
    }

    function getSoundOutputList() {
        return navigator.mediaDevices.enumerateDevices()
            .then(devices => devices.filter(device => device.kind === 'audiooutput'));
    }

    async function updateSoundOutputOptions() {
        const dropdown = getId('sound-output-dropdown');
        dropdown.innerHTML = ''; // Clear existing options

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

            // Add default sound output option at the end
            const defaultOption = createEl('option');
            defaultOption.style.fontSize = '12px';
            defaultOption.value = 'default';
            defaultOption.textContent = 'Default Sound Output';
            dropdown.appendChild(defaultOption);

        } catch (error) {
            console.error('Error updating sound output options:', error);

            // Ensure the default sound output option is added even if an error occurs
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
        '/static/sounds/musics/1.mp3',
        '/static/sounds/musics/2.mp3',
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
