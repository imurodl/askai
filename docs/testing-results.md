# AskAI Testing Results

**Date:** 2026-01-26

---

## 1. Core Functionality Tests

### 1.1 Previously Failing Queries (Now Fixed)

| Query | Before | After |
|-------|--------|-------|
| "mahsiga mash tortsa boladimi?" | "ma'lumot topilmadi" (transliteration: mash→маш instead of масҳ) | 10 relevant sources found, correct answer |
| "namoz qanday o'qiladi?" | Low relevance, irrelevant results | Detailed answer with 5 sources |
| "tahorat qanday olinadi?" | Sources found but unhelpful | AI fallback with 12-step Hanafi guide |

### 1.2 Keyword Extraction Test

**Input:** "mahsiga mash tortsa boladimi?"

**Extracted:**
```json
{
  "primary_keywords": ["маҳси", "масҳ"],
  "related_keywords": ["таҳорат", "оёқ"],
  "rewritten_query": "маҳсига масҳ тортса бўладими?"
}
```

**Result:** Keyword search found 10 results with correct Islamic terminology.

---

## 2. Controversial Questions (5 Tests)

### Test 1: Music
**Query:** "musik tinglash harommi yoki halolmi?"

**Source Type:** `ai_knowledge`

**Answer:**
> Hanafiy mazhabiga ko'ra, asosan ko'ngil ochish va shahvoniy his-tuyg'ularni qo'zg'atuvchi musiqa turlarini tinglash makruh hisoblanadi. Diniy mazmundagi, na't, madhiya kabi musiqalarni tinglashga ruxsat berilgan. Lekin bu borada mahalliy ulamolarning fikriga murojaat qilish maqsadga muvofiqdir.

---

### Test 2: Drawing/Images
**Query:** "rasm chizish harommi? rassom bo'lsa gunohmi?"

**Source Type:** `database`

**Answer:**
> Manbalarda aytilishicha, жонли нарсаларнинг расмини чизиш гуноҳ ҳисобланади. Қиёмат куни расм чизувчилар қаттиқ азобга дучор бўлишади, чунки уларга яратган нарсаларига жон киритиш буюрилади, аммо улар буни қила олишмайди. Шунингдек, фаришталар сурат бор уйга киришмайди.

---

### Test 3: Cryptocurrency
**Query:** "bitcoin va kriptovalyuta halolmi harommi?"

**Source Type:** `ai_knowledge`

**Answer:**
> Bitcoin va kriptovalyutalarning halol yoki haromligi haqida Hanafiy ulamolarining turli fikrlari bor. Ba'zi ulamolar kriptovalyutalarni noaniqlik (g'arar) va spekulyatsiya (qimor) elementlari mavjudligi sababli shubhali deb bilishadi. Boshqa ulamolar, agar kriptovalyutalar qonuniy va shaffof maqsadlarda ishlatilsa, ularda haromlik yo'q deb hisoblashadi. Bu masalada aniq bir javob yo'q...

---

### Test 4: Women Working
**Query:** "ayol kishi ishga chiqishi mumkinmi? ayollar ishlashi halolmi?"

**Source Type:** `database`

**Answer:**
> Ha, ayol kishi ishlashi mumkin. Ayollarga xos bo'lgan kasblarda, shariat doirasida ishlashga ruxsat bor. Muhimi, ishlash jarayonida shariat chegaralaridan chiqmaslik kerak.

---

### Test 5: Bank Interest/Mortgage
**Query:** "bankdan kredit olish foiz bilan harommi? ipoteka olsa bo'ladimi?"

**Source Type:** `database`

**Answer:**
> Bankdan foizli kredit olish harom. Kreditda to'lov kechiktirilganda olinadigan penyalar asosiy muammo emas, balki bankning sizga pul berib, ma'lum muddatdan keyin qaytarib olishi uchun foiz olishi ribo hisoblanadi. Ipoteka kreditlari ham shunga o'xshash bo'lgani uchun, iloji boricha ijarada turib pul yig'ib, naqdga kichikroq uy sotib olishga harakat qiling.

---

## 3. Edge Case Questions (5 Tests)

### Test 6: Prayer on Mars
**Query:** "Marsda namoz o'qisa qibla qaysi tomonda bo'ladi?"

**Source Type:** `ai_knowledge`

**Answer:**
> Marsda namoz o'qish uchun qibla yo'nalishini aniqlash murakkab masala. Bu haqda aniq ko'rsatma yo'q, chunki bu masala hozirgi fiqh kitoblarida muhokama qilinmagan. Ammo, quyidagi yo'llar bilan taxminiy yo'nalishni aniqlash mumkin:
> 1. **Yerga nisbatan:** Agar Marsda turib Yer ko'rinib tursa, Ka'ba Yerda joylashganligi sababli, Yer tomonga qarab namoz o'qish mumkin.
> 2. **Eng yaqin qiblaga nisbatan:** Agar Yer ko'rinmasa, eng yaqin qibla yo'nalishini hisoblab, shu tomonga qarab namoz o'qish mumkin.

---

### Test 7: Coma Patient Fasting
**Query:** "koma holatidagi odam ro'za tutishi kerakmi? hushsiz odam uchun namoz qazo qilinadi?"

**Source Type:** `database`

**Answer:**
> Koma holatida bo'lgan odam ro'za tutishi shart emas. Hushsiz odam uchun namoz qazo qilinadi. Chunki, namozning oxirgi vaqtida ahli farz bo'lib qolsa, faqat o'sha namozni qazo qiladi.

---

### Test 8: VR Prayer
**Query:** "virtual reallik VR ko'ylagida namoz o'qisa haqiqiy namoz hisoblanadimi?"

**Source Type:** `ai_knowledge`

**Answer:**
> Virtual reallik (VR) ko'zoynagi va kiyimida namoz o'qish haqida Hanafiy mazhabida aniq javob yo'q, chunki bu texnologiya yangi. Ammo, namozning shartlariga ko'ra:
> 1. **Joyning pokligi:** Namoz o'qiladigan joy haqiqatan ham pok bo'lishi kerak. Virtual joy bu talabga javob bermaydi.
> 2. **Qiblaga yuzlanish:** Qiblaga aniq yuzlanish shart. VRda qibla yo'nalishini aniqlash qiyin.
> 3. **Harakatlar:** Namozdagi harakatlar (qiyom, ruku, sajda) haqiqiy bo'lishi kerak.

---

### Test 9: Organ Transplant
**Query:** "odam organlarini ko'chirib o'tkazish transplantatsiya halolmi? yurak almashtirish mumkinmi?"

**Source Type:** `ai_knowledge`

**Answer:**
> Hanafiy mazhabiga ko'ra, inson a'zolarini ko'chirib o'tkazish (transplantatsiya) masalasi ulamolar o'rtasida bahsli. Ba'zi ulamolar zarurat tug'ilganda, inson hayotini saqlab qolish uchun ruxsat berish mumkin degan fikrda. Boshqa ulamolar esa, inson tanasi daxlsiz ekanligini va uni kesib, o'zgartirish mumkin emasligini aytishadi.

---

### Test 10: Robot/AI Imam
**Query:** "robot yoki sun'iy intellekt imam bo'lib namoz o'qitsa bo'ladimi?"

**Source Type:** `ai_knowledge`

**Answer:**
> Hanafiy mazhabiga ko'ra, agar robot yoki sun'iy intellekt inson kabi namoz o'qish shartlarini bajara olsa ham, uning imom bo'lishi joiz emas. Chunki imom inson bo'lishi kerak. Ammo bu masalada mahalliy ulamolarimizning fikriga murojaat qilganingiz ma'qul.

---

## 4. Summary

| Category | Total | Database | AI Knowledge |
|----------|-------|----------|--------------|
| Controversial | 5 | 3 (60%) | 2 (40%) |
| Edge Cases | 5 | 1 (20%) | 4 (80%) |
| **Total** | **10** | **4 (40%)** | **6 (60%)** |

### Observations

1. **Controversial topics** - Database had good coverage (3/5), especially for traditional fiqh questions
2. **Edge cases** - Mostly AI fallback (4/5), expected for modern/hypothetical scenarios
3. **Answer quality** - Both sources provided thoughtful, Hanafi-aligned responses
4. **Disclaimer shown** - All AI knowledge answers included verification reminder
5. **No extreme positions** - Balanced answers acknowledging different scholarly views where applicable
