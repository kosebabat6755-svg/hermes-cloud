# AI - Puter.js Docs
URL: https://docs.puter.com/AI/

AI - Puter.js Docs

# AI

The Puter.js AI feature allows you to integrate artificial intelligence capabilities into your applications.

You can use AI models from various providers to perform tasks such as chat, text-to-image, image-to-text, text-to-video, and text-to-speech conversion. And with the User-Pays Model, you don't have to set up your own API keys and top up credits, because users cover their own AI costs.

## Features 

AI Chat Text to Image Image to Text Text to Speech Voice Changer Text to Video Speech to Speech Speech to Text

#### Chat with GPT-5.4 nano 

```html
<html>
<body>
    <script src="https://js.puter.com/v2/"></script>
    <script>
        puter.ai.chat(`What is life?`, { model: "gpt-5.4-nano" }).then(puter.print);
    </script>
</body>
</html>

```

#### Generate an image of a cat using AI 

```html
<html>
<body>
    <script src="https://js.puter.com/v2/"></script>
    <script>
        // Generate an image of a cat using the default model and quality. Please note that testMode is set to true so that you can test this code without using up API credits.
        puter.ai.txt2img('A picture of a cat.', true).then((image)=>{
            document.body.appendChild(image);
        });
    </script>
</body>
</html>

```

#### Extract the text contained in an image 

```html
<html>
<body>
    <script src="https://js.puter.com/v2/"></script>
    <script>
        puter.ai.img2txt('https://assets.puter.site/letter.png').then(puter.print);
    </script>
</body>
</html>

```

#### Convert text to speech 

```html
<html>
<body>
    <script src="https://js.puter.com/v2/"></script>
    <button id="play">Speak!</button>
    <script>
        document.getElementById('play').addEventListener('click', ()=>{
            puter.ai.txt2speech(`Hello world! Puter is pretty amazing, don't you agree?`).then((audio)=>{
                audio.play();
            });
        });
    </script>
</body>
</html>

```

#### Swap a sample clip into a new voice 

```html
<html>
<body>
    <script src="https://js.puter.com/v2/"></script>
    <button id="swap">Convert voice</button>
    <script>
        document.getElementById('swap').addEventListener('click', async ()=>{
            const audio = await puter.ai.speech2speech(
                'https://puter-sample-data.puter.site/tts_example.mp3',
                {
                    voice: '21m00Tcm4TlvDq8ikWAM',
                    model: 'eleven_multilingual_sts_v2',
                    output_format: 'mp3_44100_128'
                }
            );
            audio.play();
        });
    </script>
</body>
</html>

```

#### Generate a sample Sora clip 

```html
<html>
<body>
    <script src="https://js.puter.com/v2/"></script>
    <script>
        puter.ai.txt2vid(
            "A drone shot sweeping over bioluminescent waves at night",
            true // test mode returns a sample video without spending credits
        ).then((video)=>{
            document.body.appendChild(video);
        });
    </scri