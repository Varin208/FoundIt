TEST PHOTOS FOR THE AI MATCHING
===============================

Put your test photos in THIS folder, then run (from the backend folder, venv active):

    python tune_matching.py

Each test case is a PAIR of photos: one "lost" photo and one "found" photo. Name them
like this:

    same-red-bottle_lost.jpg      <- the photo an owner would upload with a lost report
    same-red-bottle_found.jpg     <- the photo a finder would upload

Start the name with:
    same-   if the two photos show the SAME item (the AI should match them)
    diff-   if they show DIFFERENT items that look similar (the AI should NOT match them)

Good cases to try (4 to 8 is plenty):
    same-bottle-reference   a stock / reference picture of the item vs a real photo of it
    same-bottle-angle       the same item photographed from a different angle
    diff-two-bottles        two similar but different items (e.g. two different red bottles)
    diff-laptop-vs-bottle   two completely different items

OPTIONAL: describe the lost item like the lost-item form does, in a text file with the
SAME name as the photo but ending in .txt:

    same-red-bottle_lost.txt
        Red water bottle                  <- first line: the item name
        Red plastic, black lid, a sticker <- the rest: the description

    same-red-bottle_found.txt             <- (optional) the finder's notes
        Found near the cafeteria

Photos can be .jpg, .jpeg, .png or .webp. Every test photo you add stays on your computer
(this folder is ignored by git).
