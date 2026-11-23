import json
import os
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

# Fixed HTTPS origins, no environment base URL or daemon discovery.
ROUTES = {
    'openrouter': ('OPENROUTER_API_KEY', 'openrouter/free', 'https://openrouter.ai/api/v1/chat/completions'),
    'ollama': ('OLLAMA_API_KEY', 'gpt-oss:120b', 'https://ollama.com/api/chat'),
    'gemini': ('GEMINI_API_KEY', 'gemini-2.5-flash', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'),
}

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None

CLI_MODELS={'deepseek':'opencode/deepseek-v4.1-flash-free','chatgpt':'openai/gpt-5.6-luna'}
PROVIDERS={**ROUTES, **{k:(None,v,None) for k,v in CLI_MODELS.items()}}

def cli_answer(route,prompt):
    import subprocess,tempfile
    from pathlib import Path
    env={k:os.environ[k] for k in ('HOME','PATH','PREFIX','TMPDIR','LANG','ANDROID_DATA','ANDROID_ROOT','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_RUNTIME_DIR') if k in os.environ}
    with tempfile.TemporaryDirectory() as folder:
        Path(folder,'opencode.json').write_text(json.dumps({'permissions':[{'action':'*','resource':'*','effect':'deny'}]}))
        try:
            res=subprocess.run(['opencode2','run','--model',CLI_MODELS[route],'--format','json'],input='Return text only. Do not use tools.\n'+prompt,text=True,capture_output=True,cwd=folder,env=env,timeout=150)
        except subprocess.TimeoutExpired:raise ValueError(f'{route}: OpenCode timed out') from None
    parts=[]
    for line in res.stdout.splitlines():
        if not line.strip():continue
        event=json.loads(line)
        if event.get('type')=='error':raise ValueError(f'{route}: '+str(event.get('error',{}).get('type','OpenCode error')))
        if event.get('type')=='text':parts.append(event['part']['text'])
    answer=''.join(parts).strip()
    if res.returncode or not answer:raise ValueError(f'{route}: OpenCode returned no usable answer (exit {res.returncode}); check opencode2 auth list')
    return answer

def request_for(route, prompt, key):
    _, model, url = ROUTES[route]
    headers = {'Content-Type':'application/json'}
    if route == 'gemini':
        headers['x-goog-api-key'] = key
        body = {'contents':[{'parts':[{'text':prompt}]}]}
    else:
        headers['Authorization'] = 'Bearer ' + key
        body = {'model':model, 'messages':[{'role':'user','content':prompt}], 'stream':False}
    if 'Return only JSON:' in prompt:
        if route=='openrouter': body['response_format']={'type':'json_object'}
        elif route=='ollama': body['format']='json'
        elif route=='gemini': body['generationConfig']={'responseMimeType':'application/json'}
    return Request(url, data=json.dumps(body).encode(), headers=headers)

def completion(route, data):
    try:
        if route == 'gemini': text = ''.join(p.get('text','') for p in data['candidates'][0]['content']['parts'] if not p.get('thought'))
        elif route == 'ollama': text = data['message']['content']
        else:
            choice=data['choices'][0]; text=choice['message'].get('content')
            if isinstance(text,list): text=''.join(p.get('text','') for p in text if isinstance(p,dict) and p.get('type')=='text')
            if not text: raise ValueError(f'openrouter: no answer text (finish={str(choice.get("finish_reason"))[:30]})')
    except (KeyError, IndexError, TypeError, AttributeError): raise ValueError(f'{route}: no usable completion.') from None
    if not isinstance(text,str) or not text.strip(): raise ValueError(f'{route}: empty completion.')
    return text

def ask(route, prompt):
    if route in CLI_MODELS:return cli_answer(route,prompt)
    var = ROUTES[route][0]
    if not os.environ.get(var): raise ValueError(f'Set {var} in your terminal.')
    if route != 'openrouter' and os.getenv('KARIGAT_FREE_ACCOUNT') != '1':
        raise ValueError('Confirm this is a free-only account (billing disabled), then set KARIGAT_FREE_ACCOUNT=1.')
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request_for(route,prompt,os.environ[var]), timeout=100) as response:
            raw = response.read(2_000_001)
            if len(raw)>2_000_000: raise ValueError('Response exceeds size limit.')
            data = json.loads(raw)
    except HTTPError as e:
        raise ValueError(f'{route}: HTTP {e.code}; check key, quota and model availability.') from None
    return completion(route,data)
