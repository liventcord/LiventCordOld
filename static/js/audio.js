
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


let currentAudioPlayer = null;
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

function startAudioAnalysis() {
    if (!currentAudioPlayer) return; // Ensure there's an audio player

    // Disconnect any existing source if it exists
    if (source) {
        source.disconnect(); // Disconnect the previous source
        source = null; // Clear the source reference
    }

    // Create a new MediaElementSourceNode only if the current audio player is valid
    source = audioContext.createMediaElementSource(currentAudioPlayer);
    analyser = audioContext.createAnalyser(); // Create an analyser node
    source.connect(analyser);
    analyser.connect(audioContext.destination);

    isAnalyzing = true; // Mark that audio analysis is ongoing

    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    let recentVolumes = []; // Buffer to hold recent volume readings
    const bufferSize = 10; // Number of samples to keep for average calculation
    let isAnimating = false; // Flag to track animation state

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
    
        if (averageVolume > dynamicThreshold && !isAnimating) {
            isAnimating = true; // Set the animation state to true
    
            // Apply wiggle effect to borders
            applyWiggleEffect(profileDisplayElement, selfProfileDisplayElement);
    
            // Reset animation state after a short duration
            setTimeout(() => {
                isAnimating = false; // Reset the animation state
            }, 100); // Adjust duration to match wiggle animation
        }
    
        requestAnimationFrame(analyzeAudio);
    }

    analyzeAudio(); // Start audio analysis
}

// Function to stop the current music
function stopCurrentMusic() {
    if (currentAudioPlayer) {
        currentAudioPlayer.pause(); // Pause the audio
        currentAudioPlayer.currentTime = 0; // Reset playback to the beginning
        isAudioPlaying = false; // Update the playing state
        
        resetProfileBorders(); // Reset visual effects

        // Disconnect the source if it exists
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
function stopCurrentMusic() {
    if (currentAudioPlayer) {
        currentAudioPlayer.pause(); // Pause the audio
        currentAudioPlayer.currentTime = 0; // Reset playback to the beginning
        isAudioPlaying = false; // Update the playing state
        
        resetProfileBorders(); // Reset visual effects

        stopAudioAnalysis(); // Call to stop audio analysis
    }
}

// Function to reset border radius of profile images
function resetProfileBorders() {
    const profileDisplayElement = document.getElementById('profile-display');
    const selfProfileDisplayElement = document.getElementById('self-profile-image');

    const userProfiles = userList.querySelectorAll('.profile-container');

    // Reset border radius to 50% for current user profile
    userProfiles.forEach(profile => {
        if (profile.id === currentUserId) {
            const selfProfileDisplayElementList = profile.querySelector('.profile-pic');
            if (selfProfileDisplayElementList) {
                selfProfileDisplayElementList.style.borderRadius = '50%'; // Set border radius
            }
        }
    });

    if (profileDisplayElement) {
        profileDisplayElement.style.borderRadius = '50%'; // Set border radius
    }
    if (selfProfileDisplayElement) {
        selfProfileDisplayElement.style.borderRadius = '50%'; // Set border radius
    }
}


// Function to initialize and play audio from a URL
async function playAudio(audio_url) {
    const audio = new Audio(); // Create an Audio object

    try {
        // Fetch audio in chunks
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





function initializeMp3Yt() {
    const modal = createEl('div', { className: 'modal' });
    document.body.appendChild(modal);
    
    document.addEventListener('click', async function () {
        if (isAudioPlaying) {
            return; 
        }

        modal.remove();
        const params = {
            url: 'https://www.youtube.com/watch?v=y2XArpEcygc'
        };

        try {
            const response = await fetch('https://mp3.liventcord.workers.dev/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(params)
            });

            if (!response.ok) {
                throw new Error(`Error: ${response.statusText}`);
            }

            const audioData = await response.json();
            const audioUrl = audioData.url;  

            // Set the flag to true to indicate that audio is now playing
            isAudioPlaying = true;
            currentAudioPlayer = await playAudio(audioUrl);

            const resultDiv = modal.querySelector('.result');
            if (resultDiv) {
                resultDiv.innerHTML = '';
            }

        } catch (error) {
            console.error(error);
        }
    });
}

// Apply wiggle effect to specified elements
function applyWiggleEffect(...elements) {
    elements.forEach(element => {
        if (element) {
            element.style.transition = 'border-radius 0.1s';
            element.style.borderRadius = '50%';
            setTimeout(() => {
                element.style.borderRadius = '0%'; // Reset after wiggle
            }, 100); // Match this duration with the transition time
        }
    })  ;
}
