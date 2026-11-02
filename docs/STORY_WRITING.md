# Writing story scripts (`/gentruyen`)

Story mode only (`docs/STORY_MODE.md`). Archival films follow `docs/WORKFLOW.md`.

**Why this exists.** Viewers of stories 87 and 88 (2026-11-02) wrote "cốt truyện na ná như nhiều truyện đã đăng" and "chỉ có một cốt chuyện, sau đó thêm râu ria". Measured on the two scripts:
- Both had the same skeleton:
  1. A cold open with the hero in danger and a small object in his pocket.
  2. The identical line "Tôi muốn bắt đầu câu chuyện hôm nay từ khoảnh khắc ấy".
  3. The code name explained.
  4. A 2–3 minute history lecture, always in the same spot right after the code name.
  5. "Sinh năm 19xx, cha ông làm nghề…".
  6. Watch, wait, postpone, suspected.
  7. A reflective sign-off.
- Both used the same props (copper wire, a scrap of paper).
- 25–33 % of sentences had 4 words or fewer.
- There were 24–34 runs of three sentences starting with the same word.
- Story 88 had no ending.

## Rules

### Plot and structure
1. **Change the frame every episode.** Rotate how the story opens and is told. The open can be:
   - the hero's danger;
   - the enemy's side (an interrogator, a convoy commander);
   - a minor character (a child, a boatman, a wife);
   - an object's journey;
   - the aftermath (years later, a letter, a reunion);
   - a failure that the rest of the story explains.
   Keep a log in `stories/published/LOG.md` (frame, hero trade and region, signature prop, twist type) and never repeat any of the last 5.
2. **One real turn per act.** Each act must change the situation: a betrayal, a wrong guess, a cost paid, a plan that fails and forces a new one. "Waited, postponed, waited again" is not a turn. Allow at most one postponement beat per story.
3. **No padding.** Each chapter has a goal, an obstacle and a different outcome. If a scene could be cut without losing anything, cut it.
4. **Finish the story.** The climax is shown, the outcome is clear (including its cost), and the epilogue is short. Then comes the sign-off. A cliffhanger without resolution is a broken script (story 88).

### Hero, context and props
5. **A new hero every time.** Use a different trade and region, and introduce him through an action rather than his birth year or his father's trade. Give him a flaw that matters to the plot (impatience, pride, a debt, a family tie).
6. **History passages stay; move them.** The user wants real history lectures (2026-11-02: viewers like them; the complaint was only the identical skeleton) and the usual length (~55–60k characters). Keep 2–4 narrated context passages of 1–3 minutes, tied to the scene they explain (the city before the mission, the road before the journey, what came after in the epilogue). Do not put the main one in the 87/88 slot (straight after the hook and the code name); rotate where it falls.
7. **Props are unique per story.** Choose one signature object that drives the plot, never one used in earlier stories (no more copper wire, scraps of paper or silver lighters). Name it once in the hook and pay it off at the end.

### Voice and sentences
8. **Varied sentence rhythm.** Most sentences run 8–20 words, with dialogue and description mixed in. Fragments of 1–4 words are for climaxes only, under 15 % overall. Use no more than 8 runs of three sentences with the same opener. Avoid lists like "Thêm đạn. / Thêm lương khô. / Thêm phụ tùng.".
9. **No stock narrator lines.** Never use "Tôi muốn bắt đầu câu chuyện hôm nay từ khoảnh khắc…", "Trong nghề tình báo…", "Đó là phần ít được nhìn thấy…" or "Có lẽ điều khiến tôi nhớ nhất…". The narrator addresses viewers at most twice: one welcome after the hook and one sign-off.
10. **Show feelings through scenes.** Use dialogue with subtext, physical detail and small choices instead of the narrator explaining what the hero felt.

### Running the check
- `PY scripts/storycheck.py input/<story>.txt` runs after ingest and **before** `split`/`tts`.
- It compares the script with itself and with every earlier story in `stories/published/` (that folder is kept out of git). After the user confirms an upload, copy the script there.
- `!!` lines must be fixed: rewrite the script, or, if the user wrote it, report them and get the user's OK before fixing. `!` lines are to be read and judged.

## Prompt block for an outside writer (GPT/Gemini)
When the user writes with another model, give it this (Vietnamese) on top of their own prompt:

> Viết truyện hoàn chỉnh, có cao trào và kết thúc rõ ràng, rồi mới tới lời chào cuối. Không mở đầu bằng "Tôi muốn bắt đầu câu chuyện hôm nay từ khoảnh khắc…". Vẫn có các đoạn kể bối cảnh lịch sử (1–3 phút mỗi đoạn, 2–4 đoạn), nhưng đặt ở chỗ khác nhau mỗi truyện, gắn với cảnh nó giải thích, không luôn nằm ngay sau phần mở đầu và mật danh. Nhân vật chính có nghề, quê, tính cách và điểm yếu khác hẳn các truyện trước; không giới thiệu bằng "sinh năm…, cha ông làm nghề…". Mỗi truyện một đồ vật đặc trưng riêng (không dùng lại mảnh giấy, dây đồng, bật lửa bạc). Câu văn đa dạng 8–20 chữ, câu cụt 1–4 chữ chỉ ở cao trào, không lặp cùng chữ đầu câu ba lần liền. Mỗi chương phải thay đổi tình thế; không lặp vòng "chờ – hoãn – chờ".
