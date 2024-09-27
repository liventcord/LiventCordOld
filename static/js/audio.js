
let audioContext = new (window.AudioContext || window.webkitAudioContext)();
const bufferSize = 4096;

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

function joinToGuild(invite_id) {
    socket.emit('join_to_guild',{'invite_id':invite_id});
}


let currentAudioPlayer;
let isAudioPlaying = false; 
let analyser = null; // Track the AnalyserNode
let source = null; // Track the MediaElementSourceNode
let isAnalyzing = false; // Track if audio analysis is ongoing

function enableBorderMovement() {
    if (isAudioPlaying && currentAudioPlayer) {
        if (!isAnalyzing) {
            startAudioAnalysis(); // Start audio analysis if not already running
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

    // Check if `currentAudioPlayer` is a valid HTMLMediaElement
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
        if (!isAnalyzing) return; // Exit if analysis is stopped
    
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



async function playAudio(audioUrl, isYtMp3) {
    try {
        if(!currentAudioPlayer) {
            currentAudioPlayer = getId('audio-player');
        }
        if (!isYtMp3) {
            const response = await fetch(audioUrl);
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
            const audioBlob = await new Response(stream).blob();
            const audioUrlBlob = URL.createObjectURL(audioBlob); // Generate Blob URL

            // Set the Blob URL as the source for the <audio> element
            currentAudioPlayer.src = audioUrlBlob;
        } else {
            currentAudioPlayer.src = audioUrl; // Set audio URL directly for YouTube MP3 links
        }



        currentAudioPlayer.onplay = function () {
            if (isParty) {
                enableBorderMovement(); // Trigger your visual effects
            }
        };

        currentAudioPlayer.onended = function () {
            stopCurrentMusic(); // Handle when audio stops
        };

        await currentAudioPlayer.play(); // Play the audio
        isAudioPlaying = true;

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




function resetWiggleEffect(...elements) {
    elements.forEach(element => {
        if (element) {
            element.style.transition = 'none';
            element.style.borderRadius = '0%'; 
            setTimeout(() => {
                element.style.transition = 'border-radius 0.1s'; 
            }, 0);
        }
    });
}

function applyWiggleEffect(profileElement, selfProfileElement) {
    if(profileElement) {
        profileElement.classList.add('dancing-border');
    }
    if(selfProfileElement) {
        selfProfileElement.classList.add('dancing-border');
    }
    setTimeout(() => {
        if(profileElement) {
            profileElement.classList.remove('dancing-border');
        }
        if(selfProfileElement) {
            selfProfileElement.classList.remove('dancing-border');
        }
    }, 500); 
}
