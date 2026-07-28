# SKU Image Matcher

Matches low-quality, randomly-named product images ("AIAS" sheet) back to
their correct SKU name using a trusted reference catalog ("Client_Data"
sheet), based on visual similarity — not filename.

## How it works

1. Upload a `.xlsx` file with two sheets:
   - **Client_Data**: column A = `SKU_Name`, column B = `Image_Link_or_Path`
   - **AIAS**: column A = `Group_Name`, column B = `Image_Link_or_Path`
2. Every AIAS image is compared against every Client_Data image using:
   - ORB feature/keypoint matching (catches fine printed detail, e.g. an
     extra dot or different number on otherwise-identical packaging)
   - HSV color histogram correlation (overall color/pattern match)
   - Structural similarity / SSIM (shape & layout match, robust to
     resolution/quality differences)
3. Output workbook has 3 sheets:
   - **Matched**: `SKU_Name | Confidence_Score | AIAS_Group_Name | AIAS_Image_Link`
   - **Unmatched_AIAS**: AIAS items with no match in Client_Data ("clustered")
   - **Unmatched_Client**: Client SKUs with no match in AIAS ("NA — not trained in this round")

## Run locally

```bash
pip install -r requirements.txt
python make_template.py     # (re)generates the sample template, optional
python app.py
```

Visit http://localhost:5000

## Deploy (Render / Railway, free tier)

1. Push this folder to a new GitHub repo.
2. On [Render](https://render.com) or [Railway](https://railway.app):
   New → Web Service → connect your GitHub repo.
3. Build command: `pip install -r requirements.txt`
   Start command: `gunicorn app:app` (already in `Procfile`, auto-detected on Render/Heroku-style platforms)
4. Deploy. You'll get a public URL you can share.

## Tuning match sensitivity

Open `matcher_pipeline.py` and adjust:

```python
CONFIDENCE_THRESHOLD = 65.0
```

Lower it if too many real matches are landing in "Unmatched"; raise it if
near-duplicate SKUs (e.g. two mg strengths of the same product) are being
falsely matched to each other. Run a batch, look at the `Confidence_Score`
column in `Matched`, and pick a threshold that separates real matches from
false ones in your actual data.

## Notes / known limits

- Image sources can be a URL or a local file path.
- Large batches are slow because every AIAS image is compared against every
  Client_Data image (O(n·m)). For big catalogs, consider pre-filtering by
  a fast color histogram before running the slower ORB comparison.
- This is a starting template — once you run it on real data, send back the
  cases where it gets confused (e.g. two near-identical SKUs) and the
  scoring logic can be tuned further.
