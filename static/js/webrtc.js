/**
 * WebRTC video streaming utility
 */
class WebRTCHandler {
    constructor() {
        this.peerConnection = null;
        this.videoElement = document.getElementById('webrtc-video');
        this.loadingIndicator = document.getElementById('loading-indicator');
        this.errorMessage = document.getElementById('error-message');
        this.noExercise = document.getElementById('no-exercise');
        this.localStream = null;
        this.currentExercise = null;
        
        // Configuration for RTCPeerConnection with public STUN servers
        this.config = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' }
            ]
        };
    }
    
    /**
     * Initialize WebRTC connection for an exercise
     * @param {string} exerciseId - ID of the exercise to stream
     */
    async initConnection(exerciseId) {
        // Reset any existing connection
        this.resetConnection();
        
        this.currentExercise = exerciseId;
        this.showLoading();
        
        try {
            // Try the legacy method first as a fallback
            try {
                // Create image element for legacy method
                this.showLegacyStream(exerciseId);
                return; // Exit if legacy method works
            } catch (legacyError) {
                console.warn("Legacy streaming method not available, trying WebRTC", legacyError);
            }
            
            // Get local media stream
            try {
                // Get local media stream
                this.localStream = await navigator.mediaDevices.getUserMedia({ 
                    video: { width: 640, height: 480 },
                    audio: false 
                });
                
                // Display local video stream on page
                this.videoElement.srcObject = this.localStream;
                console.log("Camera accessed successfully");
                
            } catch (error) {
                console.error("Error accessing camera:", error);
                this.showError();
                throw new Error("Failed to access camera: " + error.message);
            }
            
            // Create peer connection
            this.peerConnection = new RTCPeerConnection(this.config);
            
            // Add local stream to peer connection
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });
            
            // Set up ICE candidate handling
            this.peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    console.log('New ICE candidate:', event.candidate);
                    // In a real implementation, we would send this to the server
                }
            };
            
            // Connection state handling
            this.peerConnection.oniceconnectionstatechange = () => {
                console.log('ICE connection state:', this.peerConnection.iceConnectionState);
                if (this.peerConnection.iceConnectionState === 'failed' || 
                    this.peerConnection.iceConnectionState === 'disconnected') {
                    console.warn('ICE connection failed or disconnected, trying fallback');
                    this.showLegacyStream(exerciseId);
                }
            };
            
            // Handle remote stream
            this.peerConnection.ontrack = (event) => {
                if (event.streams && event.streams[0]) {
                    this.videoElement.srcObject = event.streams[0];
                    this.hideLoading();
                }
            };
            
            // Create offer with appropriate constraints
            const offerOptions = {
                offerToReceiveAudio: false,
                offerToReceiveVideo: true
            };
            
            const offer = await this.peerConnection.createOffer(offerOptions);
            await this.peerConnection.setLocalDescription(offer);
            
            console.log('Sending offer to server...');
            
            // Send offer to server and get answer
            try {
                const response = await this.sendOfferToServer(offer, exerciseId);
                
                // Set remote description from response
                if (response && response.sdp) {
                    try {
                        await this.peerConnection.setRemoteDescription(
                            new RTCSessionDescription(response.sdp)
                        );
                        console.log('Remote description set successfully');
                        
                        // Add ICE candidates from response
                        if (response.ice_candidates) {
                            for (const candidate of response.ice_candidates) {
                                try {
                                    await this.peerConnection.addIceCandidate(
                                        new RTCIceCandidate(candidate)
                                    );
                                    console.log('Added ICE candidate');
                                } catch (iceCandidateError) {
                                    console.error('Error adding ICE candidate:', iceCandidateError);
                                }
                            }
                        }
                        
                        console.log('WebRTC connection setup completed');
                    } catch (sdpError) {
                        console.error('Error setting remote description:', sdpError);
                        this.fallbackToLegacyStream(exerciseId);
                    }
                } else {
                    console.error('Invalid response format from server');
                    this.fallbackToLegacyStream(exerciseId);
                }
            } catch (serverError) {
                console.error('Error communicating with server:', serverError);
                this.fallbackToLegacyStream(exerciseId);
            }
            
        } catch (error) {
            console.error('Error initializing WebRTC connection:', error);
            this.fallbackToLegacyStream(exerciseId);
        }
    }
    
    /**
     * Fallback to legacy streaming method
     * @param {string} exerciseId - ID of the exercise to stream
     */
    fallbackToLegacyStream(exerciseId) {
        console.log('Falling back to legacy video streaming');
        this.resetConnection();
        this.showLegacyStream(exerciseId);
    }
    
    /**
     * Set up legacy video streaming using multipart/x-mixed-replace
     * @param {string} exerciseId - ID of the exercise to stream
     */
    showLegacyStream(exerciseId) {
        // Clear any existing video source
        if (this.videoElement.srcObject) {
            const tracks = this.videoElement.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            this.videoElement.srcObject = null;
        }
        
        // Create an image element for the legacy stream
        const imgElement = document.createElement('img');
        imgElement.style.width = '100%';
        imgElement.style.height = 'auto';
        imgElement.src = `/video_feed/${exerciseId}`;
        
        // Replace video with image
        const videoContainer = document.getElementById('video-container');
        videoContainer.innerHTML = '';
        videoContainer.appendChild(imgElement);
        
        this.hideLoading();
        console.log('Switched to legacy streaming mode');
    }
    
    /**
     * Send offer to server and get answer
     * @param {RTCSessionDescriptionInit} offer - WebRTC offer
     * @param {string} exerciseId - ID of the exercise to stream
     * @returns {Promise<object>} - Server response
     */
    async sendOfferToServer(offer, exerciseId) {
        try {
            const response = await fetch('/api/rtc_offer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sdp: offer,
                    exercise: exerciseId
                })
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error sending offer to server:', error);
            throw error;
        }
    }
    
    /**
     * Reset WebRTC connection
     */
    resetConnection() {
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        
        if (this.videoElement.srcObject) {
            const tracks = this.videoElement.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            this.videoElement.srcObject = null;
        }
        
        this.currentExercise = null;
    }
    
    /**
     * Show loading indicator
     */
    showLoading() {
        this.loadingIndicator.classList.remove('d-none');
        this.errorMessage.classList.add('d-none');
        this.noExercise.classList.add('d-none');
    }
    
    /**
     * Hide loading indicator
     */
    hideLoading() {
        this.loadingIndicator.classList.add('d-none');
    }
    
    /**
     * Show error message
     */
    showError() {
        this.loadingIndicator.classList.add('d-none');
        this.errorMessage.classList.remove('d-none');
        this.noExercise.classList.add('d-none');
    }
    
    /**
     * Show no exercise selected message
     */
    showNoExercise() {
        this.loadingIndicator.classList.add('d-none');
        this.errorMessage.classList.add('d-none');
        this.noExercise.classList.remove('d-none');
    }
}

// Create global WebRTC handler instance
window.rtcHandler = new WebRTCHandler();