"""Pace per line from the transcript with per word timings: spoken duration, syllables per second (syllables counted
in the script with simple synalephas) and pause before the line.
The syllable counter is tuned for Spanish; adapt it for other languages.
Usage: pace.py <transcript.json> <script.txt>"""
import json, re, sys
def syllables(sentence):
    # counts vowel nuclei (diphthongs as one) and joins a final vowel with an initial vowel across words (synalepha)
    s = re.sub(r"[^a-záéíóúüñ ]", "", sentence.lower())
    s = re.sub(r"(?<=[aeiouáéíóú]) (?=[aeiouáéíóúh])", "", s)  # synalepha: two words fused when one ends and the next starts with a vowel
    s = s.replace(" ", "")
    nuclei = re.findall(r"[iuü]?[aeoáéó][iuy]?|[iuü][aeoáéó]|[ií][uú]|[uú][ií]|[aeiouáéíóúü]", s)
    return len(nuclei)
data = json.load(open(sys.argv[1])); lines = [l.strip() for l in open(sys.argv[2], encoding="utf-8") if l.strip()]
words = data["words"]
norm = lambda p: re.sub(r"[^\wáéíóúüñ]", "", p.lower())
i = 0; prev_end = None
for l in lines:
    n = len([w for w in l.split() if norm(w)])
    ws = words[i:i + n]; i += n
    a, z = ws[0]["start"], ws[-1]["end"]
    syl = syllables(l)
    pause = f"{a - prev_end:5.2f}" if prev_end is not None else "  -  "
    print(f"   {a:5.2f}-{z:5.2f} s  lasts {z - a:4.2f} s  {syl:2d} syllables  {syl / (z - a):4.1f} syl/s  previous pause {pause}  | {l}")
    prev_end = z
