//admittedly i failed to make this code work (finding and displaying sentences) without using gemini to figure out my errors
// generally i have almost no experience with javascript, i am certain i failed to properly implement these and the function in results.html, but they work

document.addEventListener('DOMContentLoaded', function () {
    const analyzeButton = document.getElementById('analyzeButton');

    function createWordSelector(words, frequencies) {
        const container = document.createElement('div');
        container.className = 'word-selector-container';

        const select = document.createElement('select');
        select.id = 'wordContextSelect';

        const defaultOption = new Option('Select a word to see it in context...', '', true, true);
        select.appendChild(defaultOption);

        words.forEach(word => {
            const option = new Option(`${word} (${frequencies[word]} occurrences)`, word);
            select.appendChild(option);
        });

        container.appendChild(select);
        return { container, select };
    }

    function highlightWordInSentence(sentence, word) {
        const regex = new RegExp(`(${word})`, 'gi');
        return sentence.replace(regex, '<span style="background-color: #fff3cd; padding: 2px 4px;">$1</span>');
    }

    function findSentencesContainingWord(word, text) {
        const sentences = text.match(/[^.!?]+[.!?]+/g) || [];
        return sentences.filter(sentence => sentence.toLowerCase().includes(word.toLowerCase()));
    }

    function displaySentences(word, text) {
        const container = document.createElement('div');
        container.className = 'sentences-container';

        const sentences = findSentencesContainingWord(word, text);
        if (sentences.length) {
            sentences.forEach((sentence, index) => {
                const sentenceDiv = document.createElement('div');
                sentenceDiv.innerHTML = `<span style="color: #666; margin-right: 8px;">${index + 1}. </span>${highlightWordInSentence(sentence.trim(), word)}`;
                container.appendChild(sentenceDiv);
            });
        } else {
            container.textContent = 'No sentences found containing this word.';
            container.style.textAlign = 'center';
            container.style.color = '#666';
        }

        return container;
    }

    function setupWordContextSelector(data) {
        const wordCloudContainer = document.querySelector('.word-cloud-container');
        if (!wordCloudContainer) return;

        wordCloudContainer.querySelectorAll('.word-selector-container, .sentences-container').forEach(el => el.remove());

        const sortedWords = Object.keys(data.frequencies).sort((a, b) => data.frequencies[b] - data.frequencies[a]);
        const { container, select } = createWordSelector(sortedWords, data.frequencies);

        select.addEventListener('change', function () {
            wordCloudContainer.querySelectorAll('.sentences-container').forEach(el => el.remove());
            if (this.value) {
                const sentencesDisplay = displaySentences(this.value, window.bookFullText);
                wordCloudContainer.appendChild(sentencesDisplay);
            }
        });

        wordCloudContainer.appendChild(container);
    }

    if (analyzeButton) {
        const originalHandler = analyzeButton.onclick;
        analyzeButton.onclick = async function (event) {
            if (originalHandler) await originalHandler.call(this, event);

            try {
                const identifier = window.location.pathname.split('/').pop();
                const response = await fetch(`/analyze/${identifier}`);
                const data = await response.json();

                if (data.full_text) window.bookFullText = data.full_text;

                setupWordContextSelector(data);
            } catch (error) {
                console.error('Error setting up word context:', error);
            }
        };
    }
});
