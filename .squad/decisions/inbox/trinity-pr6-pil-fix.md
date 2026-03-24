# Decision: PR #6 — PIL Image Variable Leak Fix (LOW)

**Date:** 2026-03-25
**Author:** Trinity
**Branch:** `squad/pr6-pil-leak-fix`

## Summary

Fixed LOW-severity PIL `image` memory leak in `generate.py`. The `image` variable (a PIL Image object, ~4MB) was held in scope past the `finally` block due to `image.save()` being called after `finally`. This prevented timely GC of PIL memory in batch/loop contexts.

## Change

- Moved `image.save(output_path)` and the `print` confirmation **inside the `try` block**, just before `finally`
- Added a `if image is not None:` guard so save is skipped if generation failed
- Added `image = None` to the `finally` cleanup block alongside the other `del` statements

## Rationale

PIL Image objects hold uncompressed pixel buffers in memory. Nulling `image` in `finally` releases that reference promptly — consistent with how all other pipeline variables are cleaned up. The `if image is not None` guard is defensive: on exception paths, `image` stays `None` and the save is correctly skipped.

## Diff (key lines)

**Before:**
```python
    finally:
        del base, refiner, latents, text_encoder_2, vae
        gc.collect()
        ...

    image.save(output_path)
    print(f"✅ Saved: {output_path}")
    return output_path
```

**After:**
```python
        if image is not None:
            image.save(output_path)
            print(f"✅ Saved: {output_path}")
    finally:
        del base, refiner, latents, text_encoder_2, vae
        image = None
        gc.collect()
        ...

    return output_path
```
