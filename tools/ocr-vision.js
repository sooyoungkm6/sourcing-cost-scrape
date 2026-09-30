// ocr-vision.js — 맥 내장 Vision OCR (설치·컴파일 불필요, osascript JXA + ObjC 브리지).
// 용도: 글꼴에 유니코드 매핑이 없어 pdfplumber 가 (cid:…) 만 뱉는 단가표 PDF(거래처D) 의 시행일 읽기.
//       tool-pricebook-parse.py pdf_written_dates() 가 그런 쪽만 PNG 로 렌더해 이 스크립트를 부른다.
// 사용: osascript -l JavaScript tools/ocr-vision.js page1.png [page2.png …]
//       → 파일마다 "=== 경로" 줄 다음에 인식된 텍스트 줄들
ObjC.import('Foundation');
ObjC.import('AppKit');
ObjC.import('Vision');

function run(argv) {
  if (!argv.length) { return 'usage: osascript -l JavaScript ocr-vision.js <image.png> …'; }
  const out = [];
  for (const path of argv) {
    const img = $.NSImage.alloc.initWithContentsOfFile(path);
    if (img.isNil()) { throw new Error('cannot open image: ' + path); }
    const cg = img.CGImageForProposedRectContextHints($(), $(), $());
    const req = $.VNRecognizeTextRequest.alloc.init;
    req.recognitionLevel = $.VNRequestTextRecognitionLevelAccurate;
    req.recognitionLanguages = $(['ko-KR', 'en-US']);
    req.usesLanguageCorrection = false;
    const handler = $.VNImageRequestHandler.alloc.initWithCGImageOptions(cg, $({}));
    handler.performRequestsError($([req]), $());
    out.push('=== ' + path);
    const res = req.results;
    for (let i = 0; i < res.count; i++) {
      const cands = res.objectAtIndex(i).topCandidates(1);
      if (cands.count > 0) { out.push(ObjC.unwrap(cands.objectAtIndex(0).string)); }
    }
  }
  return out.join('\n');
}
