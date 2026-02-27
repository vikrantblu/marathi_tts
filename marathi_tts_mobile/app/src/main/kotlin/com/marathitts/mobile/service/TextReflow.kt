package com.marathitts.mobile.service

/**
 * Reflows OCR-extracted text so that visual line breaks (from page
 * word-wrap) are joined into continuous sentences, while preserving
 * genuine paragraph breaks and verse/shloka structure.
 *
 * Problem: ML Kit returns '\n' at every visual line break from the
 * image.  In books, a line break is just word-wrap at page margins,
 * NOT a sentence boundary.  TTS treats '\n' as a pause, producing
 * choppy, unnatural speech.
 *
 * Rules:
 * 1. Double newlines (blank lines) → paragraph break (keep)
 * 2. Lines ending with sentence-ending punctuation → sentence boundary (keep newline)
 *    Sentence-enders: ।  ॥  .  !  ?  ;  :
 * 3. Lines ending with ॥ are verse/shloka endings → keep newline
 * 4. All other lines → join to next line with a space (prose reflow)
 */
object TextReflow {

    /**
     * Sentence-ending characters for Marathi / Sanskrit / Devanagari text.
     * If a line ends with one of these, it is a real sentence/verse boundary.
     */
    private val SENTENCE_ENDERS = charArrayOf(
        '।',   // Devanagari danda
        '॥',   // Devanagari double danda
        '.',   // Latin full stop
        '!',   // Exclamation
        '?',   // Question mark
        ';',   // Semicolon (sometimes used as list separator)
    )

    /**
     * Reflow OCR'd text: join word-wrapped lines into sentences,
     * preserving paragraph breaks and verse/shloka line structure.
     *
     * @param text Raw OCR text with visual line breaks.
     * @return Reflowed text suitable for TTS.
     */
    fun reflow(text: String): String {
        if (text.isBlank()) return text

        // Normalise line endings
        val normalised = text.replace("\r\n", "\n").replace('\r', '\n')

        // Split into paragraphs by blank lines (2+ consecutive newlines)
        val paragraphs = normalised.split(Regex("""\n\s*\n"""))

        return paragraphs.joinToString("\n\n") { para ->
            reflowParagraph(para.trim())
        }.trim()
    }

    /**
     * Reflow a single paragraph (no blank-line breaks inside).
     * Join lines that don't end with sentence-ending punctuation.
     */
    private fun reflowParagraph(paragraph: String): String {
        if (paragraph.isBlank()) return ""

        val lines = paragraph.lines()
        if (lines.size <= 1) return paragraph.trim()

        val result = StringBuilder()
        for ((index, rawLine) in lines.withIndex()) {
            val line = rawLine.trim()
            if (line.isEmpty()) continue

            result.append(line)

            // If this is the last line, don't add anything after it
            if (index == lines.lastIndex) break

            // Check if line ends with a sentence-ending character
            val lastChar = line.last()
            if (lastChar in SENTENCE_ENDERS) {
                // Sentence boundary → keep as separate line
                result.append('\n')
            } else {
                // Mid-sentence word-wrap → join with space
                result.append(' ')
            }
        }

        return result.toString()
    }
}
