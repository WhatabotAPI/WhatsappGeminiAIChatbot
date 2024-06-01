import asyncio
import websockets
import json
import ssl
import google.generativeai as genai

GEMINI_API_KEY = 'YOUR_GEMINI_API_KEY'
WHATABOT_API_KEY = 'YOUR_API_KEY'
PHONE_NUMBER = 'YOUR_PHONE_NUMBER'

model = None

async def main():
    configure_geminiai()
    client = WhatabotRealtimeClient()
    await client.run_websocket()

def configure_geminiai():
    global model
    genai.configure(api_key=GEMINI_API_KEY)
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 100, #Create short messages because Whatabot could not accept long ones.
        "response_mime_type": "text/plain",
    }
    safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    ]

    model = genai.GenerativeModel(model_name="gemini-1.5-flash",
                                generation_config=generation_config,
                                safety_settings=safety_settings)
    

def predict(prompt):
    prompt_parts = [     
        f'input: {prompt}',
        "output: ",
    ]
    if model:
        response = model.generate_content(prompt_parts) #It could take several seconds to be processed
        return response.text
    else:
        return "Gemini not initialized"


class WhatabotRealtimeClient:
    def __init__(self):
        self.api_key = WHATABOT_API_KEY
        self.chat_id = PHONE_NUMBER
        self.url = "wss://api.whatabot.io/realtimeMessages"
        self.connect_message = json.dumps({"protocol": "json", "version": 1}) + '\u001e'


    async def run_websocket(self):
        while True:
            try:
                async with websockets.connect(
                        self.url,
                        extra_headers={
                            "x-api-key": self.api_key,
                            "x-chat-id": self.chat_id,
                            "x-platform": "whatsapp"
                        },
                        ssl=ssl.create_default_context()
                ) as ws:
                    await ws.send(self.connect_message)
                    print("Connected")

                    async for message in ws:
                        await self.receive_message(ws, message)
            except Exception as ex:
                print("ERROR:", ex)

            print("Attempting to reconnect...")
            await asyncio.sleep(20)


    async def receive_message(self, ws, message):
        try:
            message = message.rstrip('\u001e')
            json_message = json.loads(message)
            arguments_array = json_message.get("arguments")
            message_target = json_message.get("target")

            if message_target == "ReceiveMessage" and arguments_array:
                text_inside_arguments = arguments_array[0]
                if text_inside_arguments:
                    gemini_response = predict(text_inside_arguments)                    
                    if gemini_response:
                        response_message = json.dumps({"type": 1, "target": "SendMessage", "arguments": [f"{gemini_response}"]}) + '\u001e'
                        await ws.send(response_message)
                        print("Message sent:", f"{gemini_response}")
                    else:
                       print("Empty response from Gemini") 
                       
        except json.JSONDecodeError:
            print("Error parsing the message")
        except Exception as ex:
            print("Error:", ex)


if __name__ == "__main__":
    asyncio.run(main())