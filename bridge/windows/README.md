# Windows codec bridge

`jy14_codec_win.cpp` loads the user's own installed `videoeditor.dll`
(JianyingPro for Windows) and calls the exported `lvve::EncryptUtils`
members, the same class the macOS bridge links against. No official file is
copied or redistributed.

## Build

Requires Visual Studio Build Tools with the C++ workload (MSVC, x64).

~~~bat
bridge\windows\build.bat
~~~

Output: `bridge\windows\out\jy14_codec_win.exe`.

## Use

~~~bat
jy14_codec_win.exe decrypt "E:\...\JianyingPro\11.6.0.14552\videoeditor.dll" draft_content.json plain.json
jy14_codec_win.exe encrypt "E:\...\JianyingPro\11.6.0.14552\videoeditor.dll" plain.json draft_content.json
~~~

The output file must not exist. Close JianyingPro before writing into a real
draft folder.

## Verified

- JianyingPro 11.6.0.14552 (x64) `videoeditor.dll`.
- Decrypting `draft_content.json` / `draft_meta_info.json` saved by 11.5.3
  yields plain JSON (`new_version` 187.0.0); encrypt → decrypt round-trips
  byte-identically.
