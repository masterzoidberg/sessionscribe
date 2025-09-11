#pragma once

#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <endpointvolume.h>
#include <functiondiscoverykeys_devpkey.h>
#include <string>
#include <thread>
#include <atomic>
#include <memory>
#include <functional>

class LoopbackCapture;
class MicCapture;

class DualRecorder {
public:
    struct Config {
        std::wstring outputPath;
        std::wstring sessionId;
        uint32_t sampleRate = 48000;
        uint32_t bitDepth = 16;
        uint32_t bufferDurationMs = 100;
    };

    using ErrorCallback = std::function<void(const std::string&)>;
    using DataCallback = std::function<void(const float*, size_t, const float*, size_t, uint64_t)>;

    DualRecorder(const Config& config);
    ~DualRecorder();

    bool Initialize();
    bool Start();
    bool Stop();
    void Cleanup();

    bool IsRecording() const { return isRecording_; }
    std::string GetLastError() const { return lastError_; }

    void SetErrorCallback(ErrorCallback callback) { errorCallback_ = callback; }
    void SetDataCallback(DataCallback callback) { dataCallback_ = callback; }

private:
    Config config_;
    std::atomic<bool> isRecording_;
    std::atomic<bool> shouldStop_;
    std::string lastError_;

    std::unique_ptr<LoopbackCapture> loopbackCapture_;
    std::unique_ptr<MicCapture> micCapture_;
    
    std::thread recordingThread_;
    ErrorCallback errorCallback_;
    DataCallback dataCallback_;

    void RecordingThreadProc();
    bool InitializeWaveFile();
    void WriteWaveHeader();
    void UpdateWaveHeader();
    
    HANDLE waveFile_;
    uint64_t totalFramesWritten_;
    uint64_t startTime_;
};