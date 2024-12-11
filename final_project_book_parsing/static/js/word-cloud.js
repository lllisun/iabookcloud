document.addEventListener('DOMContentLoaded', function () {
    // https://github.com/jasondavies/d3-cloud/issues/36 for SVG solution for fix to biggest word not displaying
    const container = d3.select("#wordCloud");
    container.selectAll("*").remove();

    const width = 800;
    const height = 500;

    const svg = container
        .attr("width", "100%")
        .attr("height", height)
        .attr("viewBox", `0 0 ${width} ${height}`)
        .attr("preserveAspectRatio", "xMidYMid meet");

    const mainGroup = svg.append("g")
        .attr("transform", `translate(${width / 2}, ${height / 2})`);

    function draw(words) {
        mainGroup.selectAll("text")
            .data(words)
            .join("text")
            .style("font-size", d => d.size + "px")
            .style("font-family", "Impact")
            .style("fill", "#000000")
            .attr("text-anchor", "middle")
            .attr("transform", d => `translate(${d.x}, ${d.y}) rotate(${d.rotate})`)
            .text(d => d.text);
    }

    const toggleDisplay = (element, state) => {
        element.style.display = state ? 'block' : 'none';
    };

    const analyzeButton = document.getElementById('analyzeButton');
    const loadingMessage = document.getElementById('loadingMessage');
    const wordCloudLoading = document.getElementById('wordCloudLoading');
    const wordCloudError = document.getElementById('wordCloudError');
    const analysisResults = document.getElementById('analysisResults');

    analyzeButton.addEventListener('click', async function () {
        const identifier = window.location.pathname.split('/').pop();

        try {
            // Display loading states
            [loadingMessage, wordCloudLoading].forEach(el => toggleDisplay(el, true));
            [analysisResults, wordCloudError].forEach(el => toggleDisplay(el, false));
            analyzeButton.disabled = true;

            const response = await fetch(`/analyze/${identifier}`);
            const data = await response.json();

            if (data.error) throw new Error(data.error);
            //not working for some reason
            [loadingMessage, wordCloudLoading].forEach(el => toggleDisplay(el, false));
            toggleDisplay(analysisResults, true);

            document.getElementById('totalWords').textContent = data.total_words.toLocaleString();
            document.getElementById('uniqueWords').textContent = data.unique_words.toLocaleString();
            document.getElementById('lexicalDiversity').textContent = `${data.lexical_diversity}%`;

            const maxWords = 300;
            const words = Object.entries(data.frequencies)
                .sort(([, a], [, b]) => b - a)
                .slice(0, maxWords)
                .map(([text, freq], index) => ({
                    text,
                    size: Math.max(15, 50 - (index * 0.5)), // dynamically scaled size
                    value: freq,
                    rotate: -45,
                    padding: 5
                }));

            // word cloud
            d3.layout.cloud()
                .size([width, height])
                .words(words)
                .padding(d => d.padding)
                .rotate(d => d.rotate)
                .fontSize(d => d.size)
                .spiral("rectangular")
                .on("end", draw)
                .start();

        } catch (error) {
            console.error('Error:', error);
            [loadingMessage, wordCloudLoading].forEach(el => toggleDisplay(el, false));
            toggleDisplay(wordCloudError, true);
            wordCloudError.textContent = 'Failed to generate word cloud. Please try again.';
        } finally {
            analyzeButton.disabled = false;
        }
    });
});
