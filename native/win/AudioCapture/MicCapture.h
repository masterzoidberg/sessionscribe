#pragma once

#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <endpointvolume.h>
#include <comdef.h>
#include <vector>
#include <string>
#include <atomic>

class MicCapture {
public:
    struct Config {
        uint32_t sampleRate = 48000;
        uint32_t bufferDurationMs = 100;
        std::wstring deviceId; // Empty for default
    };

    MicCapture(const Config& config);
    ~MicCapture();

    bool Initialize();
    bool Start();
    bool Stop();
    void Cleanup();

    // Get captured audio data (non-blocking)
    size_t GetAvailableFrames();
    bool ReadFrames(float* buffer, size_t maxFrames, size_t& framesRead, uint64_t& timestamp);

    bool IsCapturing() const { return isCapturing_; }
    std::string GetLastError() const { return lastError_; }

    uint32_t GetSampleRate() const { return actualSampleRate_; }
    uint32_t GetChannels() const { return actualChannels_; }

private:
    Config config_;
    std::atomic<bool> isCapturing_;
    std::string lastError_;

    // COM interfaces
    IMMDeviceEnumerator* deviceEnumerator_;
    IMMDevice* device_;
    IAudioClient* audioClient_;
    IAudioCaptureClient* captureClient_;

    // Audio format
    WAVEFORMATEX* mixFormat_;
    uint32_t actualSampleRate_;
    uint32_t actualChannels_;
    uint32_t bufferFrameCount_;

    // Resampling
    std::vector<float> resampleBuffer_;
    double resampleRatio_;
    size_t resampleIndex_;

    bool InitializeDevice();
    bool InitializeAudioClient();
    void SetLastError(const std::string& error);
    void SetLastError(HRESULT hr, const std::string& context);
    
    // Resampling helpers
    void ResampleToTarget(const float* input, size_t inputFrames, 
                         float* output, size_t& outputFrames);
};