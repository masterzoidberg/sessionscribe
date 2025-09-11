#include <napi.h>
#include <windows.h>
#include "DualRecorder.h"
#include <memory>
#include <string>

class DualRecorderWrapper : public Napi::ObjectWrap<DualRecorderWrapper> {
public:
    static Napi::Object Init(Napi::Env env, Napi::Object exports);
    DualRecorderWrapper(const Napi::CallbackInfo& info);

private:
    static Napi::FunctionReference constructor;
    
    Napi::Value Initialize(const Napi::CallbackInfo& info);
    Napi::Value Start(const Napi::CallbackInfo& info);
    Napi::Value Stop(const Napi::CallbackInfo& info);
    Napi::Value IsRecording(const Napi::CallbackInfo& info);
    Napi::Value GetLastError(const Napi::CallbackInfo& info);
    
    std::unique_ptr<DualRecorder> recorder_;
};

Napi::FunctionReference DualRecorderWrapper::constructor;

Napi::Object DualRecorderWrapper::Init(Napi::Env env, Napi::Object exports) {
    Napi::HandleScope scope(env);

    Napi::Function func = DefineClass(env, "DualRecorder", {
        InstanceMethod("initialize", &DualRecorderWrapper::Initialize),
        InstanceMethod("start", &DualRecorderWrapper::Start),
        InstanceMethod("stop", &DualRecorderWrapper::Stop),
        InstanceMethod("isRecording", &DualRecorderWrapper::IsRecording),
        InstanceMethod("getLastError", &DualRecorderWrapper::GetLastError)
    });

    constructor = Napi::Persistent(func);
    constructor.SuppressDestruct();

    exports.Set("DualRecorder", func);
    return exports;
}

DualRecorderWrapper::DualRecorderWrapper(const Napi::CallbackInfo& info) 
    : Napi::ObjectWrap<DualRecorderWrapper>(info) {
    
    Napi::Env env = info.Env();
    Napi::HandleScope scope(env);

    if (info.Length() < 1 || !info[0].IsObject()) {
        Napi::TypeError::New(env, "Expected config object").ThrowAsJavaScriptException();
        return;
    }

    Napi::Object config = info[0].As<Napi::Object>();
    
    DualRecorder::Config recorderConfig;
    
    if (config.Has("outputPath")) {
        std::string outputPath = config.Get("outputPath").As<Napi::String>().Utf8Value();
        recorderConfig.outputPath = std::wstring(outputPath.begin(), outputPath.end());
    }
    
    if (config.Has("sessionId")) {
        std::string sessionId = config.Get("sessionId").As<Napi::String>().Utf8Value();
        recorderConfig.sessionId = std::wstring(sessionId.begin(), sessionId.end());
    }
    
    if (config.Has("sampleRate")) {
        recorderConfig.sampleRate = config.Get("sampleRate").As<Napi::Number>().Uint32Value();
    }
    
    if (config.Has("bufferDurationMs")) {
        recorderConfig.bufferDurationMs = config.Get("bufferDurationMs").As<Napi::Number>().Uint32Value();
    }

    recorder_ = std::make_unique<DualRecorder>(recorderConfig);
}

Napi::Value DualRecorderWrapper::Initialize(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();
    
    if (!recorder_) {
        Napi::Error::New(env, "Recorder not initialized").ThrowAsJavaScriptException();
        return env.Null();
    }
    
    bool success = recorder_->Initialize();
    return Napi::Boolean::New(env, success);
}

Napi::Value DualRecorderWrapper::Start(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();
    
    if (!recorder_) {
        Napi::Error::New(env, "Recorder not initialized").ThrowAsJavaScriptException();
        return env.Null();
    }
    
    bool success = recorder_->Start();
    return Napi::Boolean::New(env, success);
}

Napi::Value DualRecorderWrapper::Stop(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();
    
    if (!recorder_) {
        Napi::Error::New(env, "Recorder not initialized").ThrowAsJavaScriptException();
        return env.Null();
    }
    
    bool success = recorder_->Stop();
    return Napi::Boolean::New(env, success);
}

Napi::Value DualRecorderWrapper::IsRecording(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();
    
    if (!recorder_) {
        return Napi::Boolean::New(env, false);
    }
    
    return Napi::Boolean::New(env, recorder_->IsRecording());
}

Napi::Value DualRecorderWrapper::GetLastError(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();
    
    if (!recorder_) {
        return Napi::String::New(env, "Recorder not initialized");
    }
    
    return Napi::String::New(env, recorder_->GetLastError());
}

Napi::Object Init(Napi::Env env, Napi::Object exports) {
    return DualRecorderWrapper::Init(env, exports);
}

NODE_API_MODULE(win_capture, Init)