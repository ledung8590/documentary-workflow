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
- `!!` lines must be fixed: rewrite the script yourself, even if the user wrote it, without asking (user rule 2026-11-12), and report what you changed. `!` lines are to be read and judged.

## Prompt block for an outside writer (GPT/Gemini)
When the user writes with another model, give it this (Vietnamese) on top of their own prompt:

> Viết truyện hoàn chỉnh, có cao trào và kết thúc rõ ràng, rồi mới tới lời chào cuối. Không mở đầu bằng "Tôi muốn bắt đầu câu chuyện hôm nay từ khoảnh khắc…". Vẫn có các đoạn kể bối cảnh lịch sử (1–3 phút mỗi đoạn, 2–4 đoạn), nhưng đặt ở chỗ khác nhau mỗi truyện, gắn với cảnh nó giải thích, không luôn nằm ngay sau phần mở đầu và mật danh. Nhân vật chính có nghề, quê, tính cách và điểm yếu khác hẳn các truyện trước; không giới thiệu bằng "sinh năm…, cha ông làm nghề…". Mỗi truyện một đồ vật đặc trưng riêng (không dùng lại mảnh giấy, dây đồng, bật lửa bạc). Câu văn đa dạng 8–20 chữ, câu cụt 1–4 chữ chỉ ở cao trào, không lặp cùng chữ đầu câu ba lần liền. Mỗi chương phải thay đổi tình thế; không lặp vòng "chờ – hoãn – chờ". Mỗi nhân vật phụ có nghề, thói quen và trò đùa chưa từng xuất hiện ở truyện trước: không dùng lại người thuộc lòng bảng giờ tàu hay con nhà đường sắt, hà mã và sở thú, thợ lên dây đàn, người chơi organ, thợ đúc chuông, người nói lắp, người sưu tầm tem, cờ vua qua thư, người đưa thư, người ghi biên lai (danh sách đầy đủ tôi gửi kèm). Tối đa hai người trong kíp có thói quen gây cười.


## New names every story (viewer comment, Military Chronicle, 2026-11-15)
"How come in all these videos there's a soldier named Beddo?" Benno (heard as "Beddo") was in four German-soldier stories in a row,
as hero, comrade and even a battery's nickname; Hinnerk, Emil, Fritz and the hometown Kassel repeated too. Every named person,
pet, nickname and hometown is new for each story. `storycheck.py` compares capitalised names with stories/published and prints
`!!` (English/German/Spanish; `!` for Vietnamese, whose syllables double as places) for any name an earlier story already used;
rename before tts. A real place or person shared on purpose (Königsberg, Bagration) goes in `stories/names_ok.txt`.


## New cast types every story (viewer comments, Military Chronicle, 2026-11-17)
On "The Last Line Before Berlin": "Railway timetable again, seriously?", "Young German men must have really liked train schedules",
"How come in every story the tank crewmen are a prototype of the crewmen in the previous videos?" The names were new, the people
were not. Measured on the published scripts: the crewman who knows the railway timetable by heart was in 4 stories (Leo, Kranich,
Thiel, Jost); the zoo hippo and its keeper in 3; a hero or driver with a musical craft (tuner, organ, bells, harmonium) in 6; "fear
shows in his body" as the hero's flaw in 3; every crew was the same set of one-quirk men.

- **A character type is used once on the channel.** A type is the trade or family trade, the party trick (recites X by heart,
  weighs everything, counts in "reels"), the speech tic, the running gag and the pet. Renaming Leo to Jost changes nothing.
- **Before writing or rewriting**, read the "Cast types already used" list in `stories/published/LOG.md` and give every named
  crew member a trade and a habit from a field no story has touched. Not every man needs a party trick: at most two per crew
  have a comic habit, the others are told through what they do and choose.
- **The hero's flaw and the secondary props rotate too** (LOG columns), not only the signature prop.
- `storycheck.py` prints `!!` for every motif family (`MOTIFS` in the script plus `stories/motifs.txt`, one `name = regex` per
  line) that the new script and an earlier story both build on, and lists the script's cast introductions to compare with the LOG.
  Fix by rewriting that character's trade, habit and every scene of the gag, not by deleting the word.
- **At delivery** (STORY_MODE step 10) add the story's cast to the LOG list and every new type to `stories/motifs.txt`, so the
  next script is checked against it.


## A new frame every story (YouTube "highly similar storyline template", 2026-11-26)
YouTube's monetization policy names "videos where characters are put in the same situation over and over again with the same
outcome (a highly similar storyline template across multiple videos)". Read in full on 2026-11-26, the 14 published soldier
stories had new names, trades and props but one frame: a diary in dated entries; a roll call of comrades by pre-war trade and one
habit near the start; the comrades die one by one with the habit echoed in the death scene; the narrator ends in Soviet captivity
(13 of 14) and is released in 1949 (12 of 14); an epilogue lists what became of every man, one dead of dysentery in a camp, the
narrator's year and age of death; a tool of his trade is spent or left behind near the end. Two Königsberg stories shared the tank
number, the zoo hippo and the calendar. New props on that frame are still the same video.

- **The frame changes, not only the props.** Against the last stories a new one differs in at least three of: the form (dated
  diary, diary kept in bursts with gaps, memoir told years later, letters to one person), how it opens (quiet day, cold open,
  the end stated first, in the middle of a job), who it is about (a fixed group, two people, changing company, an outsider, the
  chain of command), how it ends for the narrator, and the outro (no roll call of fates).
- **A title that says "Memoirs" or "Remembers" is a memoir**, not a dated diary.
- **Soviet captivity at most once in four stories**, and never with the "1949 / dysentery / died in 19xx aged" epilogue.
- **One question carries the story** (a person, a decision, a debt, a search, a job to finish), not "do they survive the retreat"
  and not an object from the hero's trade.
- **People enter by what they do.** No roll call; a pre-war trade is mentioned for at most two people.
- The story app (`Bienkich_gemini`, `src/services/diaryShape.ts`) picks the frame in code for each new script and records it in
  its memory. `storycheck.py` is the second gate: it counts the marks of the old frame (`SKELETON`) and prints `!!` when a new
  English script carries four or more marks that most earlier stories carry: rewrite the frame before tts.
