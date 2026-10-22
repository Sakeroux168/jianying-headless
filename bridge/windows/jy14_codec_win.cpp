// Windows bridge for the draft codec.
//
// Loads the user's own installed JianyingPro videoeditor.dll and calls the
// exported lvve::EncryptUtils members (the same ones the macOS bridge links
// against).  Nothing from the official install is copied or redistributed.
//
// usage:
//   jy14_codec_win.exe decrypt VIDEOEDITOR_DLL INPUT OUTPUT
//   jy14_codec_win.exe encrypt VIDEOEDITOR_DLL INPUT OUTPUT
//
// MSVC x64 member-call ABI: RCX = this, RDX = hidden return slot (when the
// member returns std::string by value), then the declared arguments.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

namespace {

#define LVVE_STR "V?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@"
constexpr const char* kEnable = "?enable@EncryptUtils@lvve@@QEAAX_N@Z";
constexpr const char* kEncrypt =
    "?encrypt@EncryptUtils@lvve@@QEAA?A" LVVE_STR "AEBV34@@Z";
constexpr const char* kDecryptValid =
    "?decrypt@EncryptUtils@lvve@@QEAA?A" LVVE_STR "AEBV34@0AEA_N@Z";

using EnableFn = void (*)(void* self, bool enabled);
using EncryptFn = std::string* (*)(void* self, std::string* ret,
                                   const std::string* input);
using DecryptFn = std::string* (*)(void* self, std::string* ret,
                                   const std::string* input,
                                   const std::string* parameters, bool* valid);

// sizeof(lvve::EncryptUtils) is not exposed; give the object generous,
// zero-initialised, 64-byte aligned storage.
alignas(64) unsigned char g_object[4096];

std::string ReadAll(const fs::path& path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) throw std::runtime_error("cannot open input: " + path.string());
  return std::string(std::istreambuf_iterator<char>(in), {});
}

void WriteNew(const fs::path& path, const std::string& data) {
  if (fs::exists(path))
    throw std::runtime_error("output exists, refusing to overwrite: " +
                             path.string());
  std::ofstream out(path, std::ios::binary);
  if (!out) throw std::runtime_error("cannot create output: " + path.string());
  out.write(data.data(), static_cast<std::streamsize>(data.size()));
  if (!out) throw std::runtime_error("write failed: " + path.string());
}

template <typename Fn>
Fn Resolve(HMODULE module, const char* name) {
  FARPROC proc = GetProcAddress(module, name);
  if (!proc) throw std::runtime_error(std::string("export not found: ") + name);
  return reinterpret_cast<Fn>(proc);
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
  if (argc != 5) {
    std::cerr << "usage: jy14_codec_win decrypt|encrypt VIDEOEDITOR_DLL INPUT "
                 "OUTPUT\n";
    return 64;
  }
  const std::wstring command = argv[1];
  if (command != L"decrypt" && command != L"encrypt") {
    std::cerr << "error: unknown command\n";
    return 64;
  }
  try {
    const fs::path dll = fs::absolute(argv[2]);
    const fs::path input_path = fs::absolute(argv[3]);
    const fs::path output_path = fs::absolute(argv[4]);
    const std::string input = ReadAll(input_path);

    // The DLL's own dependencies live next to it.
    SetDllDirectoryW(dll.parent_path().c_str());
    HMODULE module = LoadLibraryExW(
        dll.c_str(), nullptr,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if (!module)
      throw std::runtime_error("LoadLibrary failed, error " +
                               std::to_string(GetLastError()));

    void* self = g_object;
    Resolve<EnableFn>(module, kEnable)(self, true);

    std::string result;
    if (command == L"decrypt") {
      const std::string parameters = "{}";
      bool valid = false;
      Resolve<DecryptFn>(module, kDecryptValid)(self, &result, &input,
                                                &parameters, &valid);
      if (!valid || result.empty())
        throw std::runtime_error("decrypt failed or produced empty content");
    } else {
      Resolve<EncryptFn>(module, kEncrypt)(self, &result, &input);
      if (result.empty())
        throw std::runtime_error("encrypt produced empty content");
    }
    WriteNew(output_path, result);
    std::cout << "mode=" << (command == L"decrypt" ? "decrypt" : "encrypt")
              << " input_bytes=" << input.size()
              << " output_bytes=" << result.size() << "\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << "\n";
    return 1;
  }
}
