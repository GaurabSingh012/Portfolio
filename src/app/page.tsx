
"use client";

import { type FormEvent, useEffect, useState } from "react";

const navigation = [
  { label: "About", href: "#about" },
  { label: "Education", href: "#education" },
  { label: "Skills", href: "#skills" },
  { label: "Experience", href: "#experience" },
  { label: "Projects", href: "#projects" },
  { label: "Contact", href: "#contact" },
];

const projects = [
  {
    title: "CalibraKidney",
    category: "AI / COMPUTER VISION",
    description:
      "An AI-based kidney screening project using computer vision to interpret urinalysis strips and classify kidney health into G1–G4 categories.",
    technologies: ["Python", "EfficientNet-B2", "FastAPI"],
  },
  {
    title: "Manuscript Digitizer",
    category: "AI / DIGITAL PRESERVATION",
    description:
      "A manuscript digitisation project using image preprocessing, character recognition, OCR, and NLP to reconstruct readable text from historical Nepali manuscripts.",
    technologies: ["Python", "Computer Vision", "OCR", "NLP"],
  },
  {
    title: "AMR Command Assistant",
    category: "LLM / ROBOTICS",
    description:
      "A natural-language command understanding system designed to extract actions and destinations for an autonomous mobile robot.",
    technologies: ["Python", "Qwen", "LoRA", "FastAPI"],
  },
  {
    title: "CrisisMMD Analysis",
    category: "MULTIMODAL MACHINE LEARNING",
    description:
      "A multimodal classification project combining text and image representations to analyse crisis-related social media content.",
    technologies: ["PyTorch", "DistilBERT", "ResNet"],
  },
];

const skillGroups = [
  {
    title: "AI & Machine Learning",
    description: "Models, data, and intelligent applications.",
    skills: [
      "Python",
      "Machine Learning",
      "Deep Learning",
      "PyTorch",
      "NLP",
      "Computer Vision",
    ],
  },
  {
    title: "Generative AI",
    description: "Language models and retrieval-based systems.",
    skills: [
      "LLMs",
      "RAG",
      "Embeddings",
      "Semantic Search",
      "Prompt Engineering",
    ],
  },
  {
    title: "Development",
    description: "Application development and backend services.",
    skills: [
      "TypeScript",
      "JavaScript",
      "React",
      "Next.js",
      "FastAPI",
      "SQL",
    ],
  },
  {
    title: "Tools & Data",
    description: "Development workflows and data processing.",
    skills: [
      "Git",
      "GitHub",
      "Linux",
      "DVC",
      "Pandas",
      "NumPy",
      "MongoDB",
      "MySQL",
      "Postman",
    ],
  },
];

const education = {
  btech: {
    title: "Bachelor of Technology",
    field: "Artificial Intelligence and Machine Learning",
    institution: "Symbiosis Institute of Technology",
    location: "Pune, India",
    dates: "Jul 2023 – Jun 2027",
    resultLabel: "CGPA",
    result: "7.7 / 10",
    description:
      "Pursuing an undergraduate degree in Artificial Intelligence and Machine Learning, with practical project work involving computer vision, language models, and AI application development.",
  },
  class12: {
    title: "Higher Secondary Education",
    field: "Class XII",
    institution: "Tirion International College",
    location: "Kathmandu, Nepal",
    dates: "Jun 2021 – Apr 2023",
    resultLabel: "GPA",
    result: "3.44 / 4",
    description:
      "Completed higher secondary education at Tirion International College before beginning undergraduate studies in Artificial Intelligence and Machine Learning.",
  },
};

type EducationKey = keyof typeof education;

const experience = {
  role: "Service Learning Intern",
  company: "Swayam Shikshan Prayog (SSP)",
  location: "Baner, Pune, India",
  dates: "Jul 2025 – Oct 2025",
  responsibilities: [
    "Processed and analysed survey datasets using Python, Pandas, and NumPy to support data interpretation and visualisation.",
    "Cleaned, transformed, and organised collected datasets for analysis and reporting.",
  ],
};

type ContactStatus = {
  type: "success" | "error";
  message: string;
} | null;

function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="section-heading" data-reveal>
      <p className="section-eyebrow">{eyebrow}</p>
      <h2 className="section-title">{title}</h2>
      {description && (
        <p className="section-description">{description}</p>
      )}
    </div>
  );
}

export default function Home() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedEducation, setSelectedEducation] =
    useState<EducationKey>("btech");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formStatus, setFormStatus] = useState<ContactStatus>(null);

  const activeEducation = education[selectedEducation];

  useEffect(() => {
    const root = document.documentElement;
    const targets = Array.from(
      document.querySelectorAll<HTMLElement>("[data-reveal]"),
    );

    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    );

    if (
      reducedMotion.matches ||
      !("IntersectionObserver" in window)
    ) {
      targets.forEach((target) => {
        target.classList.add("is-visible");
      });
      return;
    }

    // Make content visible immediately if it is already in the viewport.
    targets.forEach((target) => {
      const bounds = target.getBoundingClientRect();

      if (bounds.top < window.innerHeight && bounds.bottom > 0) {
        target.classList.add("is-visible");
      }
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.06,
        rootMargin: "0px 0px -20px 0px",
      },
    );

    targets.forEach((target, index) => {
      target.style.setProperty(
        "--reveal-delay",
        `${(index % 3) * 55}ms`,
      );
      observer.observe(target);
    });

    // Activate the reveal CSS only after observation is configured.
    root.classList.add("reveal-ready");

    return () => {
      observer.disconnect();
      root.classList.remove("reveal-ready");
    };
  }, []);

  async function handleContactSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const form = event.currentTarget;
    const formData = new FormData(form);

    setIsSubmitting(true);
    setFormStatus(null);

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: String(formData.get("name") ?? ""),
          email: String(formData.get("email") ?? ""),
          subject: String(formData.get("subject") ?? ""),
          message: String(formData.get("message") ?? ""),
          website: String(formData.get("website") ?? ""),
        }),
      });

      const result = (await response.json().catch(() => ({}))) as {
        message?: string;
        error?: string;
      };

      if (!response.ok) {
        throw new Error(
          result.error ?? "Your message could not be sent. Please try again.",
        );
      }

      setFormStatus({
        type: "success",
        message: result.message ?? "Your message has been sent successfully.",
      });

      form.reset();
    } catch (error) {
      setFormStatus({
        type: "error",
        message:
          error instanceof Error
            ? error.message
            : "Something went wrong. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main id="home" className="portfolio-shell">
      {/* Navigation */}
      <header className="site-header">
        <nav
          aria-label="Main navigation"
          className="site-container nav-content"
        >
          <a
            href="#home"
            aria-label="Gaurab Kushwaha, home"
            className="brand"
          >
            <span className="brand-mark">G</span>
            <span className="brand-name">Gaurab Kushwaha</span>
          </a>

          <div className="desktop-nav">
            {navigation.map((item) => (
              <a key={item.href} href={item.href}>
                {item.label}
              </a>
            ))}
          </div>

          <div className="nav-actions">
            <a
              href="/resume.pdf"
              download="Gaurab-Kushwaha-Resume.pdf"
              className="button button-secondary"
            >
              Resume <span aria-hidden="true">↓</span>
            </a>

            <a href="#contact" className="button button-primary">
              Let&apos;s talk <span aria-hidden="true">↗</span>
            </a>
          </div>

          <button
            type="button"
            className="menu-toggle"
            aria-label={
              menuOpen ? "Close navigation menu" : "Open navigation menu"
            }
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span aria-hidden="true">{menuOpen ? "×" : "☰"}</span>
          </button>
        </nav>

        {menuOpen && (
          <div id="mobile-navigation" className="mobile-nav">
            <nav
              aria-label="Mobile navigation"
              className="mobile-nav-links"
            >
              {navigation.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                >
                  {item.label}
                </a>
              ))}

              <a
                href="/resume.pdf"
                download="Gaurab-Kushwaha-Resume.pdf"
                onClick={() => setMenuOpen(false)}
              >
                Download résumé ↓
              </a>

              <a href="#contact" onClick={() => setMenuOpen(false)}>
                Let&apos;s talk ↗
              </a>
            </nav>
          </div>
        )}
      </header>

      {/* Hero: the pre-composed artwork blends into the dark page. */}
      <section aria-labelledby="hero-title" className="hero-section">
        <div className="hero-artwork" aria-hidden="true" />
        <div className="hero-image-overlay" aria-hidden="true" />

        <div className="site-container hero-container">
          <div className="hero-copy">
            <p className="hero-eyebrow">
              <span aria-hidden="true" />
              AI/ML Engineer <span>·</span> GenAI &amp; RAG
            </p>

            <h1 id="hero-title" className="hero-title">
              Building practical
              <br />
              <span>AI systems.</span>
            </h1>

            <p className="hero-description">
              I&apos;m Gaurab Kushwaha, an AI/ML engineering student interested
              in machine learning, generative AI, and developing useful
              applications.
            </p>

            <div className="hero-buttons">
              <a href="#projects" className="button button-primary">
                Explore projects <span aria-hidden="true">↗</span>
              </a>

              <a
                href="/resume.pdf"
                download="Gaurab-Kushwaha-Resume.pdf"
                className="button button-secondary"
              >
                Download résumé <span aria-hidden="true">↓</span>
              </a>
            </div>

            <div className="hero-links">
              <a
                href="https://github.com/GaurabSingh012"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub ↗
              </a>

              <a
                href="https://www.linkedin.com/in/gaurab-kushwaha-837237285"
                target="_blank"
                rel="noopener noreferrer"
              >
                LinkedIn ↗
              </a>

              <span>India</span>
            </div>
          </div>

          {/* Mobile uses the same artwork below the introductory text. */}
          <div className="hero-mobile-art" aria-hidden="true" />
        </div>
      </section>

      {/* About */}
      <section id="about" className="page-section">
        <div className="section-layout about-layout">
          <div data-reveal>
            <p className="section-eyebrow">About</p>
            <h2 className="section-title">
              Interested in how AI becomes useful software.
            </h2>
          </div>

          <div data-reveal className="about-copy">
            <p>
              I&apos;m pursuing a BTech in Artificial Intelligence and Machine
              Learning at Symbiosis Institute of Technology, Pune.
            </p>

            <p>
              My interests include machine learning, computer vision, language
              models, and retrieval-augmented generation. I enjoy connecting
              model development with the software systems that make AI useful.
            </p>

            <p>
              My approach is hands-on: experiment, evaluate results, understand
              limitations, and improve the system.
            </p>
          </div>
        </div>
      </section>

      {/* Education */}
      <section id="education" className="page-section section-tinted">
        <div className="section-layout">
          <SectionHeading
            eyebrow="Education"
            title="Academic background."
            description="Select an education card to view its details."
          />

          <div className="education-cards">
            {(
              [
                ["btech", "B.Tech", "Jul 2023 – Jun 2027"],
                ["class12", "Class XII", "Jun 2021 – Apr 2023"],
              ] as const
            ).map(([key, title, dates]) => (
              <button
                key={key}
                type="button"
                aria-pressed={selectedEducation === key}
                onClick={() => setSelectedEducation(key)}
                className={`education-card ${
                  selectedEducation === key ? "education-card-active" : ""
                }`}
              >
                <span className="education-date">{dates}</span>
                <h3>{title}</h3>
                <p>{education[key].institution}</p>

                <span className="education-card-state">
                  {selectedEducation === key ? "Selected" : "View details"}
                </span>
              </button>
            ))}
          </div>

          <article className="education-details" aria-live="polite">
            <div className="education-details-main">
              <h3>{activeEducation.title}</h3>
              <p className="education-field">{activeEducation.field}</p>
              <p className="education-description">
                {activeEducation.description}
              </p>
            </div>

            <div className="education-result">
              <span>{activeEducation.resultLabel}</span>
              <strong>{activeEducation.result}</strong>
            </div>

            <div className="education-meta">
              <strong>{activeEducation.institution}</strong>
              <span>
                {activeEducation.location} · {activeEducation.dates}
              </span>
            </div>
          </article>
        </div>
      </section>

      {/* Skills */}
      <section id="skills" className="page-section">
        <div className="section-layout">
          <SectionHeading
            eyebrow="Expertise"
            title="Technologies and tools."
            description="Technologies and concepts I use while learning and developing AI-driven applications."
          />

          <div className="skills-grid">
            {skillGroups.map((group) => (
              <article
                key={group.title}
                data-reveal
                className="content-card skill-card"
              >
                <h3>{group.title}</h3>
                <p>{group.description}</p>

                <div className="tag-list">
                  {group.skills.map((skill) => (
                    <span key={skill} className="tag">
                      {skill}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Experience */}
      <section id="experience" className="page-section section-tinted">
        <div className="section-layout about-layout">
          <div data-reveal>
            <p className="section-eyebrow">Experience</p>
            <h2 className="section-title">
              Learning through real-world work.
            </h2>
          </div>

          <article data-reveal className="experience-content">
            <div className="experience-heading">
              <div>
                <h3>{experience.role}</h3>
                <p>{experience.company}</p>
                <span>{experience.location}</span>
              </div>

              <span className="experience-date">{experience.dates}</span>
            </div>

            <ul className="experience-list">
              {experience.responsibilities.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        </div>
      </section>

      {/* Projects */}
      <section id="projects" className="page-section">
        <div className="section-layout">
          <div className="projects-heading">
            <div data-reveal>
              <p className="section-eyebrow">Selected work</p>
              <h2 className="section-title">
                Projects built through experimentation.
              </h2>
              <p className="section-description">
                Practical work across computer vision, language understanding,
                and multimodal machine learning.
              </p>
            </div>

            <a
              data-reveal
              href="https://github.com/GaurabSingh012"
              target="_blank"
              rel="noopener noreferrer"
              className="text-link"
            >
              Explore GitHub ↗
            </a>
          </div>

          <div className="projects-grid">
            {projects.map((project) => (
              <article
                key={project.title}
                data-reveal
                className="content-card project-card"
              >
                <p className="project-category">{project.category}</p>
                <h3>{project.title}</h3>
                <p className="project-description">{project.description}</p>

                <div className="tag-list project-tags">
                  {project.technologies.map((technology) => (
                    <span key={technology} className="tag">
                      {technology}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Contact */}
      <section id="contact" className="page-section section-tinted">
        <div className="section-layout contact-layout">
          <div data-reveal>
            <p className="section-eyebrow">Contact</p>
            <h2 className="section-title">
              Have a project worth discussing?
            </h2>
            <p className="section-description">
              For AI projects, collaborations, or technical opportunities,
              send me a message.
            </p>

            <a
              href="mailto:gaurabkus781@gmail.com"
              className="text-link email-link"
            >
              gaurabkus781@gmail.com ↗
            </a>
          </div>

          <form
            data-reveal
            onSubmit={handleContactSubmit}
            className="contact-form"
          >
            <div aria-hidden="true" className="honeypot-field">
              <label htmlFor="contact-website">Leave this field empty</label>
              <input
                id="contact-website"
                name="website"
                type="text"
                tabIndex={-1}
                autoComplete="off"
              />
            </div>

            <div className="form-grid">
              <div>
                <label htmlFor="contact-name" className="form-label">
                  Your name
                </label>
                <input
                  id="contact-name"
                  name="name"
                  type="text"
                  autoComplete="name"
                  required
                  maxLength={100}
                  placeholder="Enter your name"
                  className="form-input"
                />
              </div>

              <div>
                <label htmlFor="contact-email" className="form-label">
                  Email address
                </label>
                <input
                  id="contact-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  maxLength={254}
                  placeholder="you@example.com"
                  className="form-input"
                />
              </div>
            </div>

            <div>
              <label htmlFor="contact-subject" className="form-label">
                Subject
              </label>
              <input
                id="contact-subject"
                name="subject"
                type="text"
                maxLength={150}
                placeholder="What is this about?"
                className="form-input"
              />
            </div>

            <div>
              <label htmlFor="contact-message" className="form-label">
                Message
              </label>
              <textarea
                id="contact-message"
                name="message"
                required
                minLength={10}
                maxLength={5000}
                rows={5}
                placeholder="Write your message..."
                className="form-input"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="button button-primary submit-button"
            >
              {isSubmitting ? "Sending…" : "Send message"}
              {!isSubmitting && <span aria-hidden="true">↗</span>}
            </button>

            {formStatus && (
              <p
                role="status"
                className={`form-status form-status-${formStatus.type}`}
              >
                {formStatus.message}
              </p>
            )}

            <p className="form-note">
              Your message is sent through the website&apos;s server.
            </p>
          </form>
        </div>
      </section>

      {/* Footer */}
      <footer className="site-footer">
        <div className="site-container footer-content">
          <a href="#home" className="footer-brand">
            Gaurab Kushwaha<span>.</span>
          </a>

          <p>
            Made with{" "}
            <span aria-hidden="true" className="footer-heart">
              ♥
            </span>{" "}
            by Gaurab Kushwaha
          </p>

          <div className="footer-links">
            <a
              href="https://github.com/GaurabSingh012"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub ↗
            </a>

            <a
              href="https://www.linkedin.com/in/gaurab-kushwaha-837237285"
              target="_blank"
              rel="noopener noreferrer"
            >
              LinkedIn ↗
            </a>

            <a href="#home">Back to top ↑</a>
          </div>
        </div>
      </footer>
    </main>
  );
}
