const textInput = document.getElementById('textInput');
const langSelect = document.getElementById('lang');
const presetSelect = document.getElementById('preset');
const modelSelect = document.getElementById('model');
const paceSlider = document.getElementById('pace');
const paceValue = document.getElementById('paceValue');
const synthesizeBtn = document.getElementById('synthesizeBtn');
const btnText = synthesizeBtn.querySelector('.btn-text');
const btnLoader = synthesizeBtn.querySelector('.btn-loader');
const resultCard = document.getElementById('resultCard');
const audioPlayer = document.getElementById('audioPlayer');
const downloadBtn = document.getElementById('downloadBtn');

paceSlider.addEventListener('input', () => {
    paceValue.textContent = paceSlider.value;
});

presetSelect.addEventListener('change', () => {
    if (presetSelect.value === 'news') {
        paceSlider.value = 0.95;
        paceValue.textContent = '0.95';
    } else if (presetSelect.value === 'fiction') {
        paceSlider.value = 0.9;
        paceValue.textContent = '0.9';
    } else if (presetSelect.value === 'education') {
        paceSlider.value = 0.85;
        paceValue.textContent = '0.85';
    }
});

synthesizeBtn.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) {
        alert('Please enter some text');
        return;
    }
    
    synthesizeBtn.disabled = true;
    btnText.textContent = 'Generating...';
    btnLoader.style.display = 'block';
    
    try {
        const response = await fetch('/synthesize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                lang: langSelect.value,
                model: modelSelect.value,
                pace: paceSlider.value,
                preset: presetSelect.value,
            }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            alert('Error: ' + (error.error || 'Failed to generate audio'));
            return;
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        audioPlayer.src = url;
        resultCard.style.display = 'block';
        resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        downloadBtn.onclick = () => {
            const a = document.createElement('a');
            a.href = url;
            a.download = 'sarvam-tts-output.wav';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        };
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        synthesizeBtn.disabled = false;
        btnText.textContent = 'Generate Audio';
        btnLoader.style.display = 'none';
    }
});
