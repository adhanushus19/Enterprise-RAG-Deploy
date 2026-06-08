# Next-Gen 3D Portfolio Architecture & Design Blueprint
**Owner**: Dhanush Appala
**Role**: Senior Data Scientist | GenAI & ML Engineer
**Theme**: Dark Futuristic (Black, Deep Blue, Neon Cyan Accents)

## 1. Full Website Structure

**A. Global Layout & Navigation**
- **Floating Glassmorphism Navbar**: Fixed at the top, blurring the background. Links to Home, Experience, Projects, AI Chat, and Contact.
- **Background Environment**: A dynamic Three.js canvas covering the entire viewport. Subtly shifting particles, glowing grids, and organic particle flows that react to scroll position.
- **Scroll-jacking & Transitions**: Smooth scroll handled via Lenis or locomotive-scroll. Sections transition like camera fly-throughs in 3D space using GSAP and Three.js cameras.

**B. Page Sections**
1. **Hero Section (Introduction)**
   - **Visuals**: A sleek, dark 3D silhouette or abstract node network that pulsates with the user's mouse movements.
   - **Content**: Animated heading: <br/> “**Senior Data Scientist | Generative AI | Enterprise ML Systems**” <br/> Typed out quickly or glowing.
   - **Call-to-Action**: "Explore My Universe" or "Talk to my AI Assistant".

2. **About Me & Career Timeline (3D Timeline)**
   - **Visuals**: A Z-axis scrolling timeline. As the user scrolls, they "fly" forward into floating milestones.
   - **Content**: 5+ years of experience across Banking, Healthcare, Retail, and Logistics.

3. **Skills Galaxy (Interactive UI)**
   - **Visuals**: Floating 3D interconnected nodes (representing LangChain, PySpark, AWS, Vertex AI, etc.).
   - **Interaction**: Hovering over a node highlights its connections and opens a sleek glass panel with examples where that skill was used.

4. **3D Project Showcase (Mandatory)**
   - **Layout**: 3D cards arranged in a spatial carousel.
   - **Project 1: AI-Powered Anomaly Detection (Logistics)**
   - **Project 2: Generative AI Fraud Detection (Banking)**
   - **Project 3: GenAI for Clinical & Pharma Analytics**
   - **Project 4: Recommendation Systems (E-Commerce)**

5. **AI Recruiter Assistant (Persistent/Modular Widget)**
   - **Location**: Floating FAB (Floating Action Button) in the bottom right corner, or a dedicated deep-dive section.
   - **UI**: A glowing 3D orb or holographic avatar. Opens into a chat interface with syntax highlighting, streaming text (like ChatGPT), and citation links.

6. **Collaboration / Contact Form**
   - **Fields**: Name, Email, Phone, Company, Job Description/Opportunity Details, Best Time to Connect, Notes.
   - **Integration**: Sent directly to adhanushus19@gmail.com.

7. **Footer**
   - Smooth gradient fade. Links to LinkedIn, Email, and a stylized "Download Resume" holographic button.

---

## 2. UI/UX Behavior Descriptions

- **Cursor Interactions**: A custom inverted cursor that interacts with Three.js elements (repelling particles, casting a slight glow on 3D objects).
- **Parallax & Depth Effects**: Layering text over 3D canvases. Foreground objects scroll faster than background elements to simulate depth.
- **Hover States**: 
  - Buttons have a liquid neon cyan filling effect on hover.
  - 3D Project Cards lift and tilt slightly towards the cursor (using framer-motion or tilt.js logic).
- **Transitions**: Instead of simple wipe transitions, camera pans through 3D scenes to switch contexts (e.g., from the Hero abstract shape directly zooming into the "Skills Galaxy").
- **Responsive Behavior**: On mobile, the Three.js canvas simplifies to reduce GPU load, and horizontal carousels replace Z-axis flying models to maintain a fluid, 60fps experience.

---

## 3. AI Agent Logic & Behavior ("Recruiter Assistant")

**A. Core Purpose & Scope**
The agent strictly acts as a conversational retrieval system grounded *only* in the provided resume. Its goal is to screen opportunities and answer technical recruiter questions professionally.

**B. System Architecture (RAG pipeline)**
- **Embeddings**: Resume parsed and embedded into a vector database (e.g., Pinecone or simple local FAISS in browser/edge node).
- **LLM**: A fast, reliable model (e.g., GPT-4o-mini or Claude 3 Haiku) accessed via a secure API route.
- **System Prompt**: 
  > "You are an AI assistant representing Dhanush Appala, a Senior Data Scientist and GenAI Engineer. Your tone is professional, confident, and senior-level. You must ONLY answer using the provided context from Dhanush's resume. Do NOT hallucinate. Keep answers concise, structured, and recruiter-friendly. Do NOT use emojis. If asked a question not covered by the resume, politely steer the conversation back to Dhanush's core competencies."

**C. Behavior & Features**
- **Trigger**: Click the glowing orb/FAB. 
- **Greeting**: "Hello. I am the AI assistant for Dhanush Appala. I can answer questions regarding his ML experience, tech stack, and enterprise AI projects. How can I help you evaluate his fit?"
- **Streaming Responses**: Real-time typing effect.
- **Citations**: Whenever mentioning a skill (e.g., PySpark), the agent adds a clickable tag that scrolls the page to the relevant project.
- **Constraints**: No emojis, no casual slang. Very precise, structured bullet points if asked about experience.

---

## 4. Prompt-Ready Design System

**A. Color Palette**
- **Background / Space**: Deep Void (`#05050A`), Dark Navy (`#0A1120`)
- **Primary Accent**: Neon Cyan (`#00F0FF`) - Used for active states, important buttons.
- **Secondary Accent**: Electric Indigo (`#5E00FF`) - Used for gradient meshes and shadows.
- **Text (Primary)**: Off-White / Ice (`#E2E8F0`)
- **Text (Secondary/Muted)**: Slate Gray (`#94A3B8`)
- **Surfaces**: Glassmorphic Panels (`rgba(255, 255, 255, 0.03)` with `backdrop-filter: blur(12px)`)

**B. Typography**
- **Headings**: `Outfit` or `Space Grotesk` (Sleek, geometric sans-serif) - Bold, uppercase/title case.
- **Body**: `Inter` - Highly legible, modern, and clean.
- **Code/Agent Output**: `JetBrains Mono` or `Fira Code`.

**C. Component Styles**
- **Cards**: 1px solid border (`rgba(0, 240, 255, 0.2)`), inner glow, deep drop shadows.
- **Buttons**: Outlined with glowing borders that fill with Neon Cyan on hover. Text turns deep Background Void color.

---

## 5. Clear Implementation Blueprint

**Phase 1: Foundation & Setup**
- **Framework**: Initialize Next.js 14+ (App Router).
- **Styling**: Configure Tailwind CSS with the Design System color palette and typography.
- **3D Engine**: Install `three`, `@react-three/fiber`, and `@react-three/drei`.

**Phase 2: UI & 3D Environment Development**
- Build global Layout, Navbar, and Footer.
- Implement the Hero Three.js canvas (Abstract nodes).
- Create generic 3D layout components: `Card3D`, `GlassContainer`.
- Integrate GSAP/ScrollTrigger & useGSAP for scroll animations.

**Phase 3: Content Implementation (Resume Grounding)**
- **Projects Section**: Build out the 4 mandatory projects with hovering 3D visuals. 
- **Timeline & Skills**: Implement the Z-axis scroll map.

**Phase 4: AI Agent Integration (The RAG piece)**
- Extract Resume text (`Dhanush_DS_Resume.pdf`).
- Set up a Next.js API Route (`/api/chat`).
- Use LangChain.js to load the resume context and handle chat history.
- Integrate the frontend UI widget with `ai` (Vercel AI SDK) for `useChat()` streaming functionality.

**Phase 5: Contact Form & Email Automation**
- Build the contact form UI.
- Integrate with **Resend** or **EmailJS** to handle form submissions and send the automated email to `adhanushus19@gmail.com`.

**Phase 6: Polish & Performance Optimization**
- Implement `<Suspense>` loaders and loading state models (e.g., spinning 3D logo).
- Audit performance (Lighthouse), ensuring WebGL canvas is optimized and responsive.
- Final deploy to Vercel.
