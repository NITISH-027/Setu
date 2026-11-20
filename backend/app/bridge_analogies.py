"""Ten draft English bridge lessons using everyday Indian examples.

These replace existing lessons by ID, not their routing or misconception tags.
They remain author-drafted and unreviewed. No claim of classroom validation.
"""
from app.models.content import ReviewRecord

BRIDGE_ANALOGIES = {
    "les_mis_sign_transposition": "A bus ticket plus a Rs 5 booking fee costs Rs 20. Let the ticket price be x: x + 5 = 20. Subtract 5 from BOTH sides: x = 15. Check: 15 + 5 = 20. A term does not magically change sign when it crosses the equals sign; we keep both sides equal by doing the same operation to each side. Try: a ticket plus Rs 3 costs Rs 12. What is the ticket price?",
    "les_mis_div_sub": "Four identical notebooks cost Rs 40: 4x = 40. Divide BOTH sides by 4 to get x = 10. But if one notebook plus a Rs 4 cover costs Rs 14, the equation is x + 4 = 14. Subtract 4 from both sides to get x = 10. Undo multiplication with division; undo addition with subtraction. Try: 3 pens cost Rs 21. Which operation finds the price of one pen?",
    "les_mis_c6_int_sub": "Imagine a shop account with a Rs 3 balance. You buy a Rs 7 pencil on credit. Your new balance is 3 - 7 = -4, meaning you owe Rs 4. On a number line start at 3 and move LEFT 7 steps, past zero to -4. Subtracting a larger positive number can give a negative result. Try: start with Rs 2 and spend Rs 5 on credit. What is the balance?",
    "les_mis_grouping_vars": "Two identical notebooks plus Rs 10 cost the same as one notebook plus Rs 30. Write 2x + 10 = x + 30. Remove one notebook's price from BOTH sides: x + 10 = 30. Then subtract 10 from both sides: x = 20. Check both bills: Rs 50 equals Rs 50. Variable terms follow the same balance rule as numbers. Try: 3x + 5 = x + 25. What can you subtract from both sides first?",
    "les_mis_add_denoms": "Use SAME-SIZED rotis: half a roti plus a quarter of a roti is not 2/6. Split the half into two quarters. Now 1/2 + 1/4 = 2/4 + 1/4 = 3/4. The denominator tells you the size of each equal piece; adding pieces does not change their size. Make denominators equal, then add only numerators. Try: 1/3 + 1/6. How many sixths make one third?",
    "les_mis_reciprocal_div": "You have 3/4 litre of lassi and cups that hold 1/4 litre each. How many full cups can you fill? Three quarter-litre portions fit, so (3/4) divided by (1/4) = 3. The rule gives the same answer: 3/4 times 4/1 = 3. Keep the first fraction, multiply by the reciprocal of the SECOND fraction. The divisor must not be zero. Try: how many 1/4-litre cups fit in 1/2 litre?",
    "les_mis_squaring_doubling": "A square rangoli has 4 rows of dots with 4 dots in each row. It has 4 squared = 4 times 4 = 16 dots. Doubling 4 would mean just 2 rows of 4, or 8 dots. Squaring a number means multiplying it by itself, not multiplying it by 2. Try: draw a 3-by-3 dot rangoli. Compare 3 squared with 3 doubled.",
    "les_mis_exp_laws": "A nursery packs seeds in groups that double at each stage. Two stages give 2 times 2 = 2 squared packets; three more stages multiply by 2 cubed. Together there are five factors of 2: 2 squared times 2 cubed = 2 to the power 5 = 32. When multiplying powers with the SAME base, ADD exponents. When raising a power to another power, multiply exponents instead. Try: 3 squared times 3 cubed has how many factors of 3?",
    "les_mis_middle_term": "Draw a square rangoli of side (10 + 2) units. Split each side into lengths 10 and 2. You get a 10-by-10 square, TWO 10-by-2 rectangles, and a 2-by-2 square. Total area = 100 + 20 + 20 + 4 = 144, not 104. In general (a + b) squared = a squared + 2ab + b squared. The two rectangles make the middle term 2ab. Try: draw the four pieces for (5 + 1) squared.",
    "les_mis_pct_raw": "A shop offers 15% off a Rs 200 school bag. Percent means out of 100, so the discount is (15/100) times 200 = Rs 30. The amount to pay is Rs 200 - Rs 30 = Rs 170. A 15% discount does not always mean Rs 15; the starting price matters. Try: find 10% off Rs 300, then the final price. Always divide the percentage number by 100 before multiplying.",
}


def apply_bridge_analogies(lessons):
    for lesson in lessons:
        if lesson.language == "en" and lesson.id in BRIDGE_ANALOGIES:
            content = BRIDGE_ANALOGIES[lesson.id]
            if lesson.content != content:
                version = lesson.review_record.item_version + 1
                lesson.content = content
                lesson.review_record = ReviewRecord(item_version=version)
    return lessons
