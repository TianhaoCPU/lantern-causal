"""Check local model loading and a short, real GPU OCR generation."""

import json
import os
import time
from pathlib import Path

import fitz
import torch
from PIL import Image
from transformers import AutoModel, AutoTokenizer

from run_ocr import ROOT, MODEL


def main():
    root = ROOT
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    torch.set_num_threads(4)
    torch.manual_seed(0)
    model_path = str(MODEL)
    print("LOADING", model_path, "GPU", os.environ.get("CUDA_VISIBLE_DEVICES"), flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    started = time.monotonic()
    model = AutoModel.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
        use_safetensors=True,
        torch_dtype=torch.bfloat16,
        attn_implementation="eager",
    ).eval().cuda()
    print("LOADED_SECONDS", round(time.monotonic() - started, 2), flush=True)
    preview = json.loads((root / "literature_ocr/inventory_preview.json").read_text())
    item = min(preview, key=lambda x: (x["pages"], x["file"]))
    with fitz.open(root / item["file"]) as doc:
        pix = doc[0].get_pixmap(dpi=200, colorspace=fitz.csRGB, alpha=False)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        native = doc[0].get_text()
    print("INFER", item, "image", image.size, flush=True)
    with torch.inference_mode():
        result = model.infer(
            tokenizer,
            image_file=image,
            crop_mode=True,
            max_crops=6,
            max_new_tokens=256,
            max_page_tokens=20000,
            no_repeat_ngram_size=35,
            ngram_window=128,
            eval_mode=True,
            return_dict=True,
            tps_interval=128,
        )
    result.update(source_pdf=item["file"], native_text_for_validation=native,
                  gpu_memory_peak_mib=torch.cuda.max_memory_allocated() / 2**20)
    (root / "literature_ocr/model_probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RESULT", result["finish_reason"], len(result["token_ids"]),
          result["time"], result["gpu_memory_peak_mib"], flush=True)
    print(result["text"][:1600], flush=True)


if __name__ == "__main__":
    main()
