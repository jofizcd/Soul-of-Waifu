// State
let currentCharacter = "";
let ws = null;
let currentMessageId = null;
let currentMessageDiv = null;
let historyOffset = 0;
const HISTORY_LIMIT = 50;
let isLoadingHistory = false;
let hasMoreHistory = true;

// Audio
let audioQueue = [];
let isPlayingAudio = false;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// Avatar
let currentAvatarMode = "Nothing";
let pixiApp = null;
let currentLive2dModel = null;
let threeScene = null;
let threeRenderer = null;
let threeCamera = null;
let currentVrm = null;
let currentMixer = null;
let clock = null;
let lookAtTarget = null;
let targetMouseX = 0;
let targetMouseY = 0;
let jitterX = 0;
let jitterY = 0;
let idleExpressionTime = 0;
let orbitControls = null;
let vrmAnimateRunning = false;

// DOM refs
const chatContainer      = document.getElementById('chat-container');
const charAvatarElement  = document.getElementById('char-avatar');
const statusTextElement  = document.getElementById('status-text');
const typingIndicator    = document.getElementById('typing-indicator');
const msgInput           = document.getElementById('msg-input');
const sendBtn            = document.getElementById('send-btn');
const stopBtn            = document.getElementById('stop-btn');
const micBtn             = document.getElementById('mic-btn');

const menuBtn            = document.getElementById('menu-btn');
const closeMenuBtn       = document.getElementById('close-menu-btn');
const mainMenu           = document.getElementById('main-menu');
const characterGrid      = document.getElementById('character-grid');

// Init
async function init() {
    marked.setOptions({
        breaks: true,
        gfm: true
    });

    try {
        const resp = await fetch('/api/config');
        const config = await resp.json();

        await loadCharacters();
        await loadBackground();

        if (config.active_character && config.active_character !== "None") {
            currentCharacter = config.active_character;
            document.getElementById('char-name').innerText = currentCharacter;
            charAvatarElement.src = `/api/avatar/${currentCharacter}`;
            statusTextElement.innerText = "Connecting to chat...";
            await loadAvatar(config.active_character);
            await loadHistory(true);
            connectWebSocket();
            setupIntersectionObserver();
        } else {
            statusTextElement.innerText = "Select a character";
            statusTextElement.className = "status-offline";
            document.getElementById('char-name').innerText = "None";
            if (mainMenu) mainMenu.classList.remove('hidden');
        }
    } catch (error) {
        console.error("Failed to load config:", error);
        statusTextElement.innerText = "Connection error";
        statusTextElement.className = "status-offline";
    }
}

// Characters
async function loadCharacters() {
    try {
        const resp = await fetch('/api/characters');
        const data = await resp.json();
        
        if (!characterGrid) return;
        characterGrid.innerHTML = "";

        if (data.characters.length === 0) {
            characterGrid.innerHTML = "<div style='grid-column: 1/-1; text-align: center; color: var(--text-dim);'>No characters found. Add them in the desktop app first.</div>";
            return;
        }

        data.characters.forEach(char => {
            const card = document.createElement('div');
            card.className = 'char-card';
            
            if (char === currentCharacter) {
                card.style.borderColor = 'rgba(255, 157, 0, 0.45)';
                card.style.background = 'rgba(255, 157, 0, 0.05)';
            }

            card.innerHTML = `
                <img class="card-avatar" src="/api/avatar/${char}" alt="${char}" loading="lazy">
                <h3 class="card-name">${char}</h3>
            `;

            card.onclick = async () => {
                if (char === currentCharacter) {
                    if (mainMenu) mainMenu.classList.add('hidden');
                    return;
                }

                statusTextElement.innerText = "Switching...";
                statusTextElement.className = "";
                if (mainMenu) mainMenu.classList.add('hidden');

                try {
                    await fetch('/api/character/switch', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ character: char })
                    });
                } catch (e) {
                    console.error("Failed to switch character", e);
                    statusTextElement.innerText = "Switching failed";
                    statusTextElement.className = "status-offline";
                }
            };

            characterGrid.appendChild(card);
        });
    } catch (e) {
        console.error("Failed to load characters list", e);
    }
}

async function loadBackground() {
    try {
        const resp = await fetch('/api/background');
        if (resp.ok) {
            document.body.style.backgroundImage = `url('/api/background?t=${Date.now()}')`;
        }
    } catch (e) {
        console.error("Failed to load background", e);
    }
}

async function loadAvatar(charName) {
    if (!charName || charName === "None") return;
    try {
        const resp = await fetch(`/api/avatar_config/${charName}`);
        const config = await resp.json();
        currentAvatarMode = config.mode;

        const canvas = document.getElementById('avatar-canvas');
        const avatarContainer = document.getElementById('avatar-container');

        if (pixiApp) {
            pixiApp.destroy(true, { children: true, texture: true, baseTexture: true });
            pixiApp = null;
            currentLive2dModel = null;
        }
        if (threeRenderer) {
            vrmAnimateRunning = false;
            threeRenderer.dispose();
            threeRenderer = null;
            threeScene = null;
            threeCamera = null;
            currentVrm = null;
            currentMixer = null;
            clock = null;
            orbitControls = null;
        }

        if (avatarContainer) avatarContainer.classList.add('hidden');
        if (canvas) canvas.classList.add('hidden');

        const toggleBtn = document.getElementById('l2d-panel-toggle');
        const controlsPanel = document.getElementById('l2d-controls-panel');
        if (toggleBtn) toggleBtn.classList.add('hidden');
        if (controlsPanel) controlsPanel.classList.add('hidden');

        if (currentAvatarMode === "Live2D Model" && config.live2d_model_file) {
            if (avatarContainer) avatarContainer.classList.remove('hidden');
            if (canvas) canvas.classList.remove('hidden');
            await initLive2D(canvas, config.live2d_model_file);
            
        } else if (currentAvatarMode === "VRM" && config.vrm_model_file) {
            if (avatarContainer) avatarContainer.classList.remove('hidden');
            if (canvas) canvas.classList.remove('hidden');
            await new Promise(resolve => requestAnimationFrame(resolve));
            await initVRM(canvas, config.vrm_model_file);
            
        } else {
            if (avatarContainer) avatarContainer.classList.add('hidden');
        }
    } catch (e) {
        console.error("Failed to load avatar config:", e);
    }
}

async function initLive2D(canvas, modelUrl) {
    const { Application } = PIXI;
    const { Live2DModel } = PIXI.live2d;

    window.PIXI = PIXI; 

    pixiApp = new Application({
        view: canvas,
        backgroundAlpha: 0,
        autoStart: true,
        resizeTo: canvas.parentElement
    });

    try {
        currentLive2dModel = await Live2DModel.from(modelUrl);
        pixiApp.stage.addChild(currentLive2dModel);

        const scaleX = pixiApp.renderer.width  / currentLive2dModel.width;
        const scaleY = pixiApp.renderer.height / currentLive2dModel.height;
        const scale  = Math.min(scaleX, scaleY) * 0.9;

        currentLive2dModel.scale.set(scale);
        currentLive2dModel.anchor.set(0.5, 0.5);
        currentLive2dModel.position.set(
            pixiApp.renderer.width  / 2,
            pixiApp.renderer.height / 2
        );

        const toggleBtn = document.getElementById('l2d-panel-toggle');
        if (toggleBtn) toggleBtn.classList.remove('hidden');

        enableLive2DDragAndScale(canvas, currentLive2dModel);

        renderLive2DControls(currentLive2dModel);

    } catch (e) {
        console.error("Live2D Load Error:", e);
    }
}

function enableLive2DDragAndScale(canvas, model) {
    if (!model) return;

    canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.05 : 0.95;
        const newScale = Math.max(0.1, Math.min(4.0, model.scale.x * factor));
        model.scale.set(newScale);
    }, { passive: false });

    model.interactive = true;
    let isDragging = false;
    let dragData = null;
    let lastPosition = { x: 0, y: 0 };

    model.on('pointerdown', (event) => {
        isDragging = true;
        dragData = event.data;
        const localPos = dragData.getLocalPosition(model.parent);
        lastPosition = {
            x: localPos.x - model.position.x,
            y: localPos.y - model.position.y
        };
    });

    model.on('pointermove', () => {
        if (isDragging && dragData) {
            const newPos = dragData.getLocalPosition(model.parent);
            model.position.set(
                newPos.x - lastPosition.x,
                newPos.y - lastPosition.y
            );
        }
    });

    const stopDragging = () => { isDragging = false; dragData = null; };
    model.on('pointerup', stopDragging);
    model.on('pointerupoutside', stopDragging);
}

function renderLive2DControls(model) {
    const exprContainer = document.getElementById('l2d-expressions-list');
    const motionContainer = document.getElementById('l2d-motions-list');
    if (!exprContainer || !motionContainer) return;

    exprContainer.innerHTML = "";
    motionContainer.innerHTML = "";

    const settings = model.internalModel.settings;
    if (!settings) return;

    const expressions = settings.expressions || [];
    if (expressions.length > 0) {
        expressions.forEach(expr => {
            const name = expr.name || expr.Name;
            if (!name) return;

            const btn = document.createElement('button');
            btn.className = 'l2d-btn';
            btn.innerText = name;
            btn.onclick = () => {
                model.expression(name);
            };
            exprContainer.appendChild(btn);
        });
    } else {
        exprContainer.innerHTML = "<span style='color: var(--text-dim); font-size: 11px;'>No available expressions</span>";
    }

    const motions = settings.motions || {};
    const motionGroups = Object.keys(motions);
    let hasMotions = false;

    motionGroups.forEach(group => {
        const groupList = motions[group] || [];
        groupList.forEach((motion, index) => {
            hasMotions = true;
            const btn = document.createElement('button');
            btn.className = 'l2d-btn';

            const file = motion.file || motion.File || "";
            const cleanName = file ? file.split('/').pop().replace('.mtn', '').replace('.motion3.json', '') : `${group} [${index}]`;

            btn.innerText = cleanName;
            btn.onclick = () => {
                model.motion(group, index);
            };
            motionContainer.appendChild(btn);
        });
    });

    if (!hasMotions) {
        motionContainer.innerHTML = "<span style='color: var(--text-dim); font-size: 11px;'>No available motions</span>";
    }
}

const togglePanelBtn = document.getElementById('l2d-panel-toggle');
const closePanelBtn = document.getElementById('l2d-panel-close');
const controlsPanel = document.getElementById('l2d-controls-panel');

if (togglePanelBtn && controlsPanel) {
    togglePanelBtn.onclick = (e) => {
        e.stopPropagation();
        controlsPanel.classList.toggle('hidden');
    };
}
if (closePanelBtn && controlsPanel) {
    closePanelBtn.onclick = (e) => {
        e.stopPropagation();
        controlsPanel.classList.add('hidden');
    };
}

async function initVRM(canvas, modelUrl) {
    const THREE         = await import('three');
    const { GLTFLoader }                                  = await import('three/addons/loaders/GLTFLoader.js');
    const { OrbitControls }                               = await import('three/addons/controls/OrbitControls.js');
    const { VRMLoaderPlugin, VRMUtils, VRMLookAt }        = await import('@pixiv/three-vrm');

    const container = canvas.parentElement;
    const W = container.clientWidth  || 400;
    const H = container.clientHeight || 600;

    threeRenderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    threeRenderer.setSize(W, H);
    threeRenderer.setPixelRatio(window.devicePixelRatio);
    threeRenderer.outputEncoding        = THREE.sRGBEncoding;
    threeRenderer.physicallyCorrectLights = true;
    threeRenderer.shadowMap.enabled     = true;

    threeCamera = new THREE.PerspectiveCamera(30.0, W / H, 0.1, 20.0);
    threeCamera.position.set(0.0, 1.4, 2.0);

    threeScene = new THREE.Scene();

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    threeScene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, Math.PI);
    directionalLight.position.set(1.0, 1.0, 1.0).normalize();
    directionalLight.castShadow = true;
    threeScene.add(directionalLight);

    lookAtTarget = new THREE.Object3D();
    threeCamera.add(lookAtTarget);
    threeScene.add(threeCamera);

    orbitControls = new OrbitControls(threeCamera, threeRenderer.domElement);
    orbitControls.screenSpacePanning = true;
    orbitControls.target.set(0.0, 1.0, 0.0);
    orbitControls.update();

    class VRMSmoothLookAt extends VRMLookAt {
        constructor(humanoid, applier) {
            super(humanoid, applier);
            this.smoothFactor  = 10.0;
            this.yawLimit      = 45.0;
            this.pitchLimit    = 45.0;
            this._yawDamped    = 0.0;
            this._pitchDamped  = 0.0;
            this._v3A          = new THREE.Vector3();
        }
        update(delta) {
            if (this.target && this.autoUpdate) {
                this.lookAt(this.target.getWorldPosition(this._v3A));
                if (Math.abs(this._yaw) > this.yawLimit ||
                    Math.abs(this._pitch) > this.pitchLimit) {
                    this._yaw   = 0.0;
                    this._pitch = 0.0;
                }
                const k = 1.0 - Math.exp(-this.smoothFactor * delta);
                this._yawDamped   += (this._yaw   - this._yawDamped)   * k;
                this._pitchDamped += (this._pitch - this._pitchDamped) * k;
                this.applier.applyYawPitch(this._yawDamped, this._pitchDamped);
                this._needsUpdate = false;
            }
            if (this._needsUpdate) {
                this._needsUpdate = false;
                this.applier.applyYawPitch(this._yaw, this._pitch);
            }
        }
    }

    const loader = new GLTFLoader();
    loader.register(parser => new VRMLoaderPlugin(parser));

    loader.load(
        modelUrl,
        (gltf) => {
            currentVrm = gltf.userData.vrm;

            VRMUtils.removeUnnecessaryVertices(gltf.scene);
            VRMUtils.combineSkeletons(gltf.scene);
            VRMUtils.combineMorphs(currentVrm);

            gltf.scene.traverse(obj => {
                obj.frustumCulled = false;
                if (obj.isMesh) {
                    obj.castShadow    = true;
                    obj.receiveShadow = true;
                }
            });

            const smoothLookAt = new VRMSmoothLookAt(
                currentVrm.humanoid,
                currentVrm.lookAt.applier
            );
            smoothLookAt.copy(currentVrm.lookAt);
            currentVrm.lookAt        = smoothLookAt;
            currentVrm.lookAt.target = threeCamera;

            threeScene.add(currentVrm.scene);

            VRMUtils.rotateVRM0(currentVrm);

            currentMixer = new THREE.AnimationMixer(currentVrm.scene);

            startBlinking();

            loadIdleAnimation();

            console.log("[VRM] Model loaded successfully");
            window.vrmLoaded = true;
            if (window.onVrmLoaded) window.onVrmLoaded();
        },
        (progress) => {
            if (progress.total > 0) {
                const pct = Math.round(progress.loaded / progress.total * 100);
                console.log(`[VRM] Loading model… ${pct}%`);
            }
        },
        (error) => {
            console.error("[VRM] Load error:", error);
        }
    );

    document.addEventListener('mousemove', (e) => {
        targetMouseX =  (e.clientX / window.innerWidth)  * 2 - 1;
        targetMouseY = -(e.clientY / window.innerHeight) * 2 + 1;
    });

    const onResize = () => {
        if (!threeRenderer || !threeCamera) return;
        const nW = container.clientWidth;
        const nH = container.clientHeight;
        if (nW === 0 || nH === 0) return;
        threeCamera.aspect = nW / nH;
        threeCamera.updateProjectionMatrix();
        threeRenderer.setSize(nW, nH);
    };
    window.addEventListener('resize', onResize);

    function startBlinking() {
        if (!currentVrm || !currentVrm.expressionManager) return;
        const delay = 2000 + Math.random() * 6000;
        setTimeout(() => {
            if (!currentVrm || !currentVrm.expressionManager) return;
            const duration = 80 + Math.random() * 120;
            currentVrm.expressionManager.setValue('blink', 1.0);
            setTimeout(() => {
                if (currentVrm && currentVrm.expressionManager) {
                    currentVrm.expressionManager.setValue('blink', 0.0);
                }
            }, duration);
            startBlinking();
        }, delay);
    }

    async function loadIdleAnimation() {
        try {
            const { loadMixamoAnimation } = await import('loadMixamo');
            const idleUrl = '/app/utils/emotions/vrm/expressions/neutral.fbx';
            const clip    = await loadMixamoAnimation(idleUrl, currentVrm);
            if (clip && currentMixer) {
                const action   = currentMixer.clipAction(clip);
                action.loop    = THREE.LoopRepeat;
                action.play();
                console.log("[VRM] Idle animation started");
            }
        } catch (e) {
            console.log("[VRM] Idle animation skipped (not served over HTTP):", e.message);
        }
    }

    function updateIdleJitter(deltaTime) {
        idleExpressionTime -= deltaTime;
        if (idleExpressionTime <= 0) {
            idleExpressionTime = 2.0 + Math.random() * 3.0;
            if (Math.random() > 0.4) {
                jitterX = (Math.random() - 0.5) * 1.5;
                jitterY = (Math.random() - 0.5) * 1.0;
            } else {
                jitterX = 0;
                jitterY = 0;
            }
            if (currentVrm && currentVrm.expressionManager) {
                const rand = Math.random();
                currentVrm.expressionManager.setValue('relaxed',  0);
                currentVrm.expressionManager.setValue('surprised', 0);
                if (rand < 0.3) {
                    currentVrm.expressionManager.setValue('relaxed', 0.10 + Math.random() * 0.1);
                } else if (rand > 0.9) {
                    currentVrm.expressionManager.setValue('surprised', 0.05 + Math.random() * 0.08);
                }
            }
        }
    }

    clock = new THREE.Clock();
    vrmAnimateRunning = true;

    function animate() {
        if (!vrmAnimateRunning || !threeRenderer || !threeScene) return;
        requestAnimationFrame(animate);

        const delta = clock.getDelta();

        updateIdleJitter(delta);

        if (lookAtTarget) {
            const time        = clock.elapsedTime;
            const breathOffset = Math.sin(time * 1.5) * 0.05;

            const finalTargetX = targetMouseX * 3.0 + jitterX;
            const finalTargetY = targetMouseY * 2.0 + jitterY + breathOffset;

            lookAtTarget.position.x += (finalTargetX - lookAtTarget.position.x) * 5.0 * delta;
            lookAtTarget.position.y += (finalTargetY - lookAtTarget.position.y) * 5.0 * delta;
            lookAtTarget.position.z  = -5.0;
        }

        if (currentMixer) currentMixer.update(delta);
        if (currentVrm)   currentVrm.update(delta);
        if (orbitControls) orbitControls.update();

        threeRenderer.render(threeScene, threeCamera);
    }

    animate();
}

function setupIntersectionObserver() {
    chatContainer.addEventListener('scroll', async () => {
        if (chatContainer.scrollTop <= 50 && !isLoadingHistory && hasMoreHistory) {
            const oldScrollHeight = chatContainer.scrollHeight;
            await loadHistory(false);
            chatContainer.scrollTop = chatContainer.scrollHeight - oldScrollHeight;
        }
    });
}

async function loadHistory(isFirstLoad = false) {
    if (!currentCharacter || isLoadingHistory || !hasMoreHistory) return;
    isLoadingHistory = true;
    try {
        const resp = await fetch(
            `/api/history/${currentCharacter}?offset=${historyOffset}&limit=${HISTORY_LIMIT}`
        );
        const data = await resp.json();
        if (data.history && data.history.length > 0) {
            const frag = document.createDocumentFragment();
            data.history.forEach(msg => {
                const el = createMessageElement(msg.text, msg.is_user ? 'user' : 'waifu', msg.id);
                frag.appendChild(el);
            });
            if (isFirstLoad) {
                chatContainer.innerHTML = "";
                chatContainer.appendChild(frag);
                scrollToBottom(true);
            } else {
                chatContainer.insertBefore(frag, chatContainer.firstChild);
            }
            historyOffset += data.history.length;
            if (data.history.length < HISTORY_LIMIT) hasMoreHistory = false;
        } else {
            hasMoreHistory = false;
        }
    } catch (error) {
        console.error("Failed to load history:", error);
    }
    isLoadingHistory = false;
}

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onopen = () => {
        console.log("WebSocket connected");
        statusTextElement.innerText  = "Online";
        statusTextElement.className  = "status-online";
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            switch (data.type) {
                case "chunk":            hideTypingIndicator(); handleIncomingChunk(data.text); break;
                case "message_start":    showTypingIndicator(); currentMessageId = Date.now().toString(); currentMessageDiv = null; break;
                case "message_end":      hideTypingIndicator(); currentMessageId = null; currentMessageDiv = null; break;
                case "user_message":     { const el = createMessageElement(data.text, 'user', null); chatContainer.appendChild(el); scrollToBottom(true); break; }
                case "character_changed": location.reload(); break;
                case "message_deleted":  { const el = document.getElementById(`msg-${data.id}`); if (el) el.remove(); break; }
                case "message_edited":   {
                    const el = document.getElementById(`msg-${data.id}`);
                    if (el) { el.dataset.rawText = data.text; const c = el.querySelector('.msg-content'); if (c) c.innerHTML = marked.parse(data.text); }
                    break;
                }
                case "audio":            handleIncomingAudio(data.data); break;
                case "avatar_telemetry": handleAvatarTelemetry(data.volume); break;
                case "emotion_changed":  handleAvatarEmotion(data.emotion); break;
            }
        } catch (e) {
            console.error("Failed to parse WebSocket message:", e);
        }
    };

    ws.onclose = () => {
        console.log("WebSocket disconnected");
        statusTextElement.innerText = "Disconnected";
        statusTextElement.className = "status-offline";
        setTimeout(connectWebSocket, 3000);
    };
}

function handleIncomingChunk(text) {
    if (!currentMessageDiv) {
        currentMessageDiv = createMessageElement("", 'waifu', currentMessageId);
        chatContainer.appendChild(currentMessageDiv);
    }
    currentMessageDiv.dataset.rawText += text;
    const contentDiv = currentMessageDiv.querySelector('.msg-content');
    if (contentDiv) contentDiv.innerHTML = marked.parse(currentMessageDiv.dataset.rawText);
    scrollToBottom();
}

function createMessageElement(text, side, id) {
    const div = document.createElement('div');
    div.className = `message ${side}`;
    if (id) div.id = `msg-${id}`;
    div.dataset.rawText = text || "";

    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';
    contentDiv.innerHTML = marked.parse(text || "");
    div.appendChild(contentDiv);

    if (id) {
        const controls = document.createElement('div');
        controls.className = 'msg-controls';

        const editBtn = document.createElement('button');
        editBtn.className = 'control-btn';
        editBtn.title = "Edit";
        editBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>`;
        editBtn.onclick = () => enableEditMode(div, id);
        controls.appendChild(editBtn);

        if (side === 'waifu') {
            const regenBtn = document.createElement('button');
            regenBtn.className = 'control-btn';
            regenBtn.title = "Regenerate";
            regenBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>`;
            regenBtn.onclick = () => regenerateMessage(id);
            controls.appendChild(regenBtn);
        }

        const delBtn = document.createElement('button');
        delBtn.className = 'control-btn';
        delBtn.title = "Delete";
        delBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`;
        delBtn.onclick = () => deleteMessage(id);
        controls.appendChild(delBtn);

        div.appendChild(controls);

        div.addEventListener('click', (e) => {
        if (e.target.closest('.msg-controls') || e.target.closest('.edit-input') || e.target.closest('.edit-actions')) {
            return;
        }
        
        const controls = div.querySelector('.msg-controls');
        if (controls) {
            document.querySelectorAll('.msg-controls.mobile-active').forEach(p => {
                if (p !== controls) p.classList.remove('mobile-active');
            });
            controls.classList.toggle('mobile-active');
        }
    });
    }
    return div;
}

function enableEditMode(div, id) {
    if (div.querySelector('.edit-input')) return;
    const contentDiv = div.querySelector('.msg-content');
    const rawText    = div.dataset.rawText;

    const input      = document.createElement('textarea');
    input.className  = 'edit-input';
    input.value      = rawText;

    const actions    = document.createElement('div');
    actions.className = 'edit-actions';

    const cancelEdit = () => { input.remove(); actions.remove(); contentDiv.style.display = 'block'; };

    const saveBtn    = document.createElement('button');
    saveBtn.innerText = 'Save';
    saveBtn.onclick  = async () => {
        const newText = input.value;
        const resp = await fetch(`/api/messages/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ character: currentCharacter, text: newText })
        });
        if (resp.ok) { cancelEdit(); div.dataset.rawText = newText; contentDiv.innerHTML = marked.parse(newText); }
    };

    const cancelBtn  = document.createElement('button');
    cancelBtn.innerText = 'Cancel';
    cancelBtn.onclick = cancelEdit;

    actions.appendChild(cancelBtn);
    actions.appendChild(saveBtn);

    contentDiv.style.display = 'none';
    div.insertBefore(input,   div.querySelector('.msg-controls'));
    div.insertBefore(actions, div.querySelector('.msg-controls'));
}

async function deleteMessage(id) {
    if (!confirm("Delete this message?")) return;
    await fetch(`/api/messages/${id}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ character: currentCharacter })
    });
}

async function regenerateMessage(id) {
    await fetch(`/api/messages/${id}/regenerate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ character: currentCharacter })
    });
}

function showTypingIndicator() {
    typingIndicator.classList.remove('hidden');
    typingIndicator.classList.add('visible');
    chatContainer.appendChild(typingIndicator);
    scrollToBottom();
}

function hideTypingIndicator() {
    typingIndicator.classList.remove('visible');
    typingIndicator.classList.add('hidden');
}

function sendMessage() {
    const text = msgInput.value.trim();
    if (!text || !currentCharacter || !ws || ws.readyState !== WebSocket.OPEN) return;

    msgInput.value = "";
    msgInput.style.height = 'auto';
    msgInput.disabled = true;
    sendBtn.classList.remove('active');

    ws.send(JSON.stringify({ type: "user_input", character: currentCharacter, text }));

    const el = createMessageElement(text, 'user', Date.now().toString());
    chatContainer.appendChild(el);
    scrollToBottom(true);
    showTypingIndicator();

    msgInput.disabled = false;
    msgInput.focus();
}

function scrollToBottom(force = false) {
    if (force) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return;
    }
    
    const threshold = 150;
    const isNearBottom = (chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight) < threshold;

    if (isNearBottom) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

msgInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

sendBtn.onclick           = sendMessage;
msgInput.onkeypress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
};
msgInput.oninput          = (e) => { sendBtn.classList.toggle('active', e.target.value.trim().length > 0); };
if (stopBtn) stopBtn.onclick = async () => { await fetch('/api/generation/stop', { method: 'POST' }); hideTypingIndicator(); };

function handleIncomingAudio(b64Audio) {
    audioQueue.push(b64Audio);
    if (!isPlayingAudio) playNextAudio();
}

function playNextAudio() {
    if (audioQueue.length === 0) { isPlayingAudio = false; return; }
    isPlayingAudio = true;
    const audio = new Audio("data:audio/wav;base64," + audioQueue.shift());
    audio.onended  = () => playNextAudio();
    audio.onerror  = () => playNextAudio();
    audio.play().catch(() => playNextAudio());
}

function handleAvatarTelemetry(volume) {
    if (currentLive2dModel) {
        currentLive2dModel.internalModel.coreModel
            .setParameterValueById("ParamMouthOpenY", volume);
    }
    if (currentVrm && currentVrm.expressionManager) {
        currentVrm.expressionManager.setValue('aa', volume);
    }
}

function handleAvatarEmotion(emotion) {
    if (currentLive2dModel) {
        try { currentLive2dModel.expression(emotion); } catch (e) {}
    }
    if (currentVrm && currentVrm.expressionManager) {
        const presets = ['neutral', 'happy', 'angry', 'sad', 'relaxed', 'surprised'];
        presets.forEach(p => currentVrm.expressionManager.setValue(p, 0));

        const map = {
            amusement: 'happy', joy: 'happy', love: 'happy', admiration: 'happy',
            anger: 'angry', annoyance: 'angry', disapproval: 'angry',
            sadness: 'sad', disappointment: 'sad', remorse: 'sad',
            surprise: 'surprised', realization: 'surprised',
            relief: 'relaxed', optimism: 'relaxed'
        };
        const expr = map[emotion.toLowerCase()] || 'neutral';
        currentVrm.expressionManager.setValue(expr, 1.0);
    }
}

async function toggleRecording() {
    if (!isRecording) {
        try {
            const stream    = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder   = new MediaRecorder(stream);
            audioChunks     = [];

            mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
            mediaRecorder.onstop = async () => {
                micBtn.classList.remove('recording');
                isRecording = false;
                if (audioChunks.length === 0) return;

                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const formData  = new FormData();
                formData.append('audio',     audioBlob, 'recording.webm');
                formData.append('character', currentCharacter);
                showTypingIndicator();

                try {
                    const resp   = await fetch('/api/voice/stt', { method: 'POST', body: formData });
                    const result = await resp.json();
                    if (result.status === 'ok' && result.text) {
                        const el = createMessageElement(result.text, 'user', Date.now().toString());
                        chatContainer.appendChild(el);
                        scrollToBottom();
                    } else {
                        hideTypingIndicator();
                    }
                } catch (e) {
                    hideTypingIndicator();
                    console.error("STT Error:", e);
                }
                stream.getTracks().forEach(t => t.stop());
            };

            mediaRecorder.start();
            isRecording = true;
            micBtn.classList.add('recording');
        } catch (e) {
            console.error("Microphone access denied:", e);
            alert("Failed to access the microphone.");
        }
    } else {
        if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
    }
}

if (micBtn) micBtn.onclick = toggleRecording;

if (menuBtn && mainMenu) {
    menuBtn.onclick = (e) => {
        e.stopPropagation();
        mainMenu.classList.remove('hidden');
        loadCharacters();
    };
}

if (closeMenuBtn && mainMenu) {
    closePanelBtn.onclick = (e) => {
        e.stopPropagation();
        mainMenu.classList.add('hidden');
    };
    closeMenuBtn.onclick = (e) => {
        e.stopPropagation();
        mainMenu.classList.add('hidden');
    };
}

init();