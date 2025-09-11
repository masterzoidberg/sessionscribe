{
  "targets": [
    {
      "target_name": "win_capture",
      "sources": [
        "src/binding.cpp",
        "AudioCapture/LoopbackCapture.cpp",
        "AudioCapture/MicCapture.cpp", 
        "AudioCapture/DualRecorder.cpp"
      ],
      "include_dirs": [
        "<!@(node -p \"require('node-addon-api').include\")",
        "AudioCapture"
      ],
      "libraries": [
        "-lole32",
        "-loleaut32",
        "-luuid",
        "-lwinmm"
      ],
      "defines": [
        "NAPI_DISABLE_CPP_EXCEPTIONS",
        "WIN32_LEAN_AND_MEAN",
        "NOMINMAX"
      ],
      "cflags_cc": [
        "/std:c++17"
      ],
      "msvs_settings": {
        "VCCLCompilerTool": {
          "AdditionalOptions": ["/std:c++17"]
        }
      },
      "dependencies": [
        "<!(node -p \"require('node-addon-api').gyp\")"
      ]
    }
  ]
}