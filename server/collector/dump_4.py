#!/usr/bin/env python3

# Copyright 2023 Google LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Script to dump clip / session metadata for users."""

import csv
import datetime
import json
import os
import re

import google.api_core.exceptions
from google.cloud import firestore
from constants import _MATCH_USERS, _METADATA_DUMP_ID

# ---------------------------------------------------------------------------
# Static globals / configuration
# ---------------------------------------------------------------------------

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
assert PROJECT_ID, "must specify the environment variable GOOGLE_CLOUD_PROJECT"

BUCKET_NAME = f"{PROJECT_ID}.appspot.com"
SERVICE_ACCOUNT_EMAIL = f"{PROJECT_ID}@appspot.gserviceaccount.com"

# Firestore layout:
# collector (collection)
#   users (document)
#     <username> (collection)
#       data (document)
#         save_clip (collection of clipData-... docs)
#
CLIP_COLLECTION_NAME = "save_clip"

# If you want to force specific users, put them here.
# Right now we explicitly include "lenovo_p2"; add/remove names as needed.
# If this list is empty, the script will auto-discover users.
USERNAMES = ["test"]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_iso_timestamp(ts: str) -> datetime.datetime:
  """Parse Firestore-style ISO timestamps, handling trailing 'Z'."""
  if ts is None:
    raise ValueError("Timestamp is None")

  # Firestore often uses a trailing 'Z' to indicate UTC; Python 3.10's
  # datetime.fromisoformat() cannot parse that directly.
  if isinstance(ts, str) and ts.endswith("Z"):
    ts = ts[:-1] + "+00:00"  # convert 'Z' to '+00:00'

  return datetime.datetime.fromisoformat(ts)


# ---------------------------------------------------------------------------
# Firestore helpers
# ---------------------------------------------------------------------------

def get_data(username: str):
  """Obtain the clip and session data from Firestore for a single user."""
  db = firestore.Client()
  collection_path = f"collector/users/{username}/data/{CLIP_COLLECTION_NAME}"
  print(f"[DEBUG] Reading collection: {collection_path}")
  c_ref = db.collection(collection_path)

  clips = []
  sessions = []

  docs = list(c_ref.stream())
  print(f"[DEBUG] Found {len(docs)} Firestore documents for user {username}")

  for doc_data in docs:
    # Clip documents
    if doc_data.id.startswith("clipData-"):
      doc_dict = doc_data.to_dict()

      # Use the 'data' map if present, otherwise fall back to top-level.
      data = doc_dict.get("data") or doc_dict

      if not data:
        print(f"[DEBUG] Skipping doc {doc_data.id} for {username}: empty data")
        continue

      clip_id = data.get("clipId")
      if not clip_id:
        print(f"[DEBUG] Skipping {doc_data.id} for {username}: no clipId")
        continue

      m = re.match(r"[^-]+-s(\d{3})-(\d{3})", clip_id)
      if not m:
        print(f"[DEBUG] Skipping {doc_data.id} for {username}: clipId format mismatch ({clip_id})")
        continue

      session_index = int(m.group(1))
      clip_index = int(m.group(2))

      filename = data.get("filename")
      if not filename:
        print(f"[DEBUG] Skipping {doc_data.id} for {username}: no filename")
        continue

      m = re.match(r"^(tutorial-)?(.+[^-]+)-[^-]+-s(\d{3})-.+\.mp4$", filename)
      if not m:
        print(f"[DEBUG] Skipping {doc_data.id} for {username}: filename format mismatch ({filename})")
        continue

      tutorial_prefix = m.group(1)
      user_id = m.group(2)
      if session_index != int(m.group(3)):
        print(f"[DEBUG] Skipping {doc_data.id} for {username}: session index mismatch")
        continue

      prompt_data = data.get("promptData") or {}
      simple_clip = {
          "userId": user_id,
          "sessionIndex": session_index,
          "clipIndex": clip_index,
          "filename": filename,
          "promptText": prompt_data.get("prompt"),
          "valid": data.get("valid"),
      }

      if tutorial_prefix:
        simple_clip["tutorial"] = True

      start_s, end_s = get_clip_bounds_in_video(data)
      if start_s is not None:
        simple_clip["start_s"] = start_s
      if end_s is not None:
        simple_clip["end_s"] = end_s

      clips.append({"summary": simple_clip, "full": doc_dict})

    # Session documents (if you ever store them in this collection)
    elif doc_data.id.startswith("sessionData-"):
      doc_dict = doc_data.to_dict()
      data = doc_dict.get("data") or doc_dict
      if data:
        sessions.append(data)

  return (clips, sessions)


def get_clip_bounds_in_video(clip_data: dict):
  """Determine the clip start and end time based on button pushes and swipes."""
  video_start = clip_data.get("videoStart")
  if not video_start:
    return (None, None)

  clip_start = clip_data.get("startButtonDownTimestamp")
  if not clip_start:
    clip_start = clip_data.get("startButtonUpTimestamp")
  if not clip_start:
    return (None, None)

  clip_end = clip_data.get("restartButtonDownTimestamp")
  if not clip_end:
    clip_end = clip_data.get("swipeForwardTimestamp")
  if not clip_end:
    clip_end = clip_data.get("swipeBackTimestamp")
  if not clip_end:
    return (None, None)

  # Use helper to handle trailing 'Z' / timezone
  video_start_time = _parse_iso_timestamp(video_start)
  clip_start_time = _parse_iso_timestamp(clip_start)
  clip_end_time = _parse_iso_timestamp(clip_end)

  start_s = (clip_start_time - video_start_time).total_seconds()
  end_s = (clip_end_time - video_start_time).total_seconds()
  return (start_s, end_s)


def clean():
  """Remove all the metadata files from the local filesystem."""
  if os.path.exists(f"{_METADATA_DUMP_ID}.json"):
    os.system(f"rm -rf {_METADATA_DUMP_ID}.json")
  print(f"Removed {_METADATA_DUMP_ID}.json")

  if os.path.exists(f"{_METADATA_DUMP_ID}.csv"):
    os.system(f"rm -rf {_METADATA_DUMP_ID}.csv")
  print(f"Removed {_METADATA_DUMP_ID}.csv")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
  db = firestore.Client()

  all_clips = []
  all_sessions = []

  # Decide which usernames to process
  if USERNAMES:
    usernames = USERNAMES
  else:
    # Auto-discover users under collector/users
    root_doc = db.document("collector/users")
    usernames = []
    for user_coll in root_doc.collections():
      username = user_coll.id
      if _MATCH_USERS and not _MATCH_USERS.match(username):
        continue
      usernames.append(username)

  for username in usernames:
    retry = True
    print(f"Getting data for user: {username}")
    while retry:
      retry = False
      try:
        clips, sessions = get_data(username)
        print(f"{username} {len(clips)} clips, {len(sessions)} sessions")
        all_clips.extend(clips)
        all_sessions.extend(sessions)
      except google.api_core.exceptions.RetryError:
        print("timed out, retrying")
        retry = True

  # Sort clips by filename then clipIndex (inside 'summary')
  all_clips.sort(
      key=lambda x: (
          x["summary"].get("filename", ""),
          x["summary"].get("clipIndex", 0),
      )
  )

  # Sort sessions if they have filename
  all_sessions.sort(key=lambda x: (x.get("filename", "")))

  # Write JSON dump
  with open(f"{_METADATA_DUMP_ID}.json", "w") as f:
    f.write(json.dumps({
        "clips": all_clips,
        "sessions": all_sessions,
    }, indent=2))
    f.write("\n")

  # Create a CSV file for import / analysis.
  csv_path = f"{_METADATA_DUMP_ID}.csv"
  print(f"Writing csv to {csv_path}")

  with open(csv_path, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)

    # Header: one column per key in summary (+ start/end)
    writer.writerow([
        "userId",
        "sessionIndex",
        "clipIndex",
        "filename",
        "valid",
        "start_s",
        "end_s",
        "promptText",
    ])

    # One row per (valid) clip; include even if start/end are missing.
    for clip in all_clips:
      summary = clip["summary"]

      # Keep the original behavior of skipping clips marked invalid
      if not summary.get("valid"):
        continue

      row = [
          summary.get("userId"),
          summary.get("sessionIndex"),
          summary.get("clipIndex"),
          summary.get("filename"),   # full filename, same as JSON
          summary.get("valid"),
          summary.get("start_s"),    # may be None -> empty in CSV
          summary.get("end_s"),      # may be None -> empty in CSV
          summary.get("promptText"),
      ]
      writer.writerow(row)


if __name__ == "__main__":
  main()
