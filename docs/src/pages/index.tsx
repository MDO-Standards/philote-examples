import type { ReactNode } from "react";
import Link from "@docusaurus/Link";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Layout from "@theme/Layout";
import styles from "./index.module.css";

/* ── Animated SVG: discipline pipeline visualization ── */
function NetworkVisualization() {
    return (
        <svg viewBox="0 0 760 300" className={styles.netSvg}>
            <defs>
                <pattern
                    id="grid"
                    width="40"
                    height="40"
                    patternUnits="userSpaceOnUse"
                >
                    <path
                        d="M 40 0 L 0 0 0 40"
                        fill="none"
                        stroke="#00d4ff"
                        strokeWidth="0.3"
                        opacity="0.12"
                    />
                </pattern>
                <filter id="node-glow">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                    </feMerge>
                </filter>
                <linearGradient
                    id="link-grad"
                    x1="0%"
                    y1="0%"
                    x2="100%"
                    y2="0%"
                >
                    <stop offset="0%" stopColor="#00d4ff" stopOpacity="0.9" />
                    <stop offset="50%" stopColor="#00d4ff" stopOpacity="0.5" />
                    <stop
                        offset="100%"
                        stopColor="#00d4ff"
                        stopOpacity="0.9"
                    />
                </linearGradient>
            </defs>

            <rect width="760" height="300" fill="url(#grid)" opacity="0.5" />

            {/* Connection lines from disciplines to OpenMDAO */}
            <line
                x1="160"
                y1="80"
                x2="600"
                y2="150"
                stroke="url(#link-grad)"
                strokeWidth="1.2"
                strokeDasharray="4 4"
                opacity="0.55"
            />
            <line
                x1="160"
                y1="150"
                x2="600"
                y2="150"
                stroke="url(#link-grad)"
                strokeWidth="1.2"
                strokeDasharray="4 4"
                opacity="0.55"
            />
            <line
                x1="160"
                y1="220"
                x2="600"
                y2="150"
                stroke="url(#link-grad)"
                strokeWidth="1.2"
                strokeDasharray="4 4"
                opacity="0.55"
            />

            {/* Discipline nodes (left) */}
            {[
                { y: 80, label: "NACA", sub: "geometry" },
                { y: 150, label: "XFOIL", sub: "aerodynamics" },
                { y: 220, label: "OAS", sub: "vlm" },
            ].map((s, i) => (
                <g key={i}>
                    <circle
                        cx="160"
                        cy={s.y}
                        r="8"
                        fill="#ff6b35"
                        filter="url(#node-glow)"
                        className={styles.netNode}
                        style={{ animationDelay: `${i * 0.3}s` }}
                    />
                    <text
                        x="100"
                        y={s.y + 4}
                        fill="#8fa4b8"
                        fontSize="10"
                        fontFamily="var(--font-mono)"
                        textAnchor="end"
                        letterSpacing="0.08em"
                    >
                        {s.label}
                    </text>
                    <text
                        x="100"
                        y={s.y + 16}
                        fill="#5a7089"
                        fontSize="7"
                        fontFamily="var(--font-mono)"
                        textAnchor="end"
                    >
                        {s.sub}
                    </text>
                </g>
            ))}

            {/* Integration node (right) */}
            <circle
                cx="600"
                cy="150"
                r="9"
                fill="#00d4ff"
                filter="url(#node-glow)"
                className={styles.netNode}
            />
            <text
                x="600"
                y="186"
                fill="#8fa4b8"
                fontSize="10"
                fontFamily="var(--font-mono)"
                textAnchor="middle"
                letterSpacing="0.08em"
            >
                OPENMDAO
            </text>
            <text
                x="600"
                y="200"
                fill="#5a7089"
                fontSize="8"
                fontFamily="var(--font-mono)"
                textAnchor="middle"
            >
                integration
            </text>

            {/* Packets traveling along the wires */}
            <circle
                r="3"
                fill="#ff6b35"
                className={styles.netPacket}
                style={{
                    offsetPath:
                        "path('M 160 80 L 600 150')",
                    animationDelay: "0s",
                }}
            />
            <circle
                r="3"
                fill="#00d4ff"
                className={styles.netPacketReverse}
                style={{
                    offsetPath:
                        "path('M 160 80 L 600 150')",
                    animationDelay: "1.7s",
                }}
            />
            <circle
                r="3"
                fill="#ff6b35"
                className={styles.netPacket}
                style={{
                    offsetPath:
                        "path('M 160 150 L 600 150')",
                    animationDelay: "0.6s",
                }}
            />
            <circle
                r="3"
                fill="#00d4ff"
                className={styles.netPacketReverse}
                style={{
                    offsetPath:
                        "path('M 160 150 L 600 150')",
                    animationDelay: "2.3s",
                }}
            />
            <circle
                r="3"
                fill="#ff6b35"
                className={styles.netPacket}
                style={{
                    offsetPath:
                        "path('M 160 220 L 600 150')",
                    animationDelay: "1.2s",
                }}
            />
            <circle
                r="3"
                fill="#00d4ff"
                className={styles.netPacketReverse}
                style={{
                    offsetPath:
                        "path('M 160 220 L 600 150')",
                    animationDelay: "2.9s",
                }}
            />

            {/* Footer label */}
            <text
                x="380"
                y="278"
                fill="#5a7089"
                fontSize="9"
                fontFamily="var(--font-mono)"
                textAnchor="middle"
                letterSpacing="0.12em"
            >
                gRPC // PHILOTE-EXAMPLES
            </text>
        </svg>
    );
}

/* ── Feature card ── */
type FeatureItem = {
    label: string;
    title: string;
    description: string;
};

const features: FeatureItem[] = [
    {
        label: "GEOMETRY",
        title: "NACA Airfoil Generator",
        description:
            "Analytical NACA 4-digit airfoil coordinate generation with full gradient support. Outputs Selig-format contours compatible with any panel method solver.",
    },
    {
        label: "AERODYNAMICS",
        title: "XFOIL Panel Method",
        description:
            "Wraps the XFOIL executable for viscous and inviscid airfoil analysis. Computes lift, drag, and moment coefficients at specified flight conditions.",
    },
    {
        label: "VLM",
        title: "OpenAeroStruct VLM",
        description:
            "Packages a complete OpenAeroStruct vortex-lattice method analysis as a single Philote discipline using OpenMdaoSubProblem.",
    },
    {
        label: "INTEGRATION",
        title: "OpenMDAO Workflows",
        description:
            "All disciplines plug into OpenMDAO via RemoteExplicitComponent. Chain them together for coupled multidisciplinary analyses over gRPC.",
    },
];

function FeatureCard({ label, title, description }: FeatureItem) {
    return (
        <div className={styles.featureCard}>
            <span className={styles.featureLabel}>{label}</span>
            <h3 className={styles.featureTitle}>{title}</h3>
            <p className={styles.featureDesc}>{description}</p>
        </div>
    );
}

/* ── Code preview ── */
function CodePreview() {
    const code = `from philote_examples import NacaDiscipline, XfoilDiscipline
from philote_mdo.openmdao import RemoteExplicitComponent
import openmdao.api as om

prob = om.Problem()
prob.model.add_subsystem("naca",
    RemoteExplicitComponent(channel=naca_channel),
    promotes_outputs=["airfoil_x", "airfoil_y"])
prob.model.add_subsystem("xfoil",
    RemoteExplicitComponent(channel=xfoil_channel),
    promotes_inputs=["airfoil_x", "airfoil_y"])
prob.setup()
prob.run_model()`;

    return (
        <div className={styles.codeBlock}>
            <div className={styles.codeHeader}>
                <span className={styles.codeDotOrange} />
                <span className={styles.codeDotCyan} />
                <span className={styles.codeFilename}>run_analysis.py</span>
            </div>
            <pre className={styles.codePre}>{code}</pre>
        </div>
    );
}

/* ── Stat ── */
function Stat({ value, label }: { value: string; label: string }) {
    return (
        <div className={styles.stat}>
            <div className={styles.statValue}>{value}</div>
            <div className={styles.statLabel}>{label}</div>
        </div>
    );
}

/* ── Hero ── */
function Hero() {
    const { siteConfig } = useDocusaurusContext();
    return (
        <header className={styles.hero}>
            <div className={styles.heroGlow} />
            <div className={styles.heroInner}>
                <div className={styles.heroSuper}>
                    Philote MDO Example Disciplines
                </div>
                <h1 className={styles.heroTitle}>{siteConfig.title}</h1>
                <p className={styles.heroTagline}>
                    Ready-to-run example disciplines demonstrating NACA airfoil
                    geometry, XFOIL aerodynamic analysis, and OpenAeroStruct
                    VLM -- all served over gRPC
                </p>
                <div className={styles.heroCtas}>
                    <Link
                        to="/docs/getting-started/installation"
                        className={styles.ctaPrimary}
                    >
                        Get Started
                    </Link>
                    <Link
                        to="/docs/tutorials/naca-xfoil-analysis"
                        className={styles.ctaSecondary}
                    >
                        View Tutorials
                    </Link>
                </div>
                <div className={styles.netWrap}>
                    <NetworkVisualization />
                </div>
            </div>
        </header>
    );
}

/* ── Page ── */
export default function Home(): ReactNode {
    return (
        <Layout description="Example Philote MDO disciplines for airfoil geometry, aerodynamic analysis, and vortex-lattice methods">
            <Hero />

            <section className={styles.statsBar}>
                <div className={styles.statsInner}>
                    <Stat value="Python 3.8+" label="Runtime" />
                    <Stat value="3" label="Disciplines" />
                    <Stat value="gRPC" label="Transport" />
                    <Stat value="Apache-2" label="License" />
                </div>
            </section>

            <main className={styles.featuresSection}>
                <div className={styles.featuresInner}>
                    <div className={styles.sectionHeader}>
                        <span className={styles.sectionLabel}>
                            Example Disciplines
                        </span>
                        <h2 className={styles.sectionTitle}>
                            Production-Ready Philote Discipline Examples
                        </h2>
                    </div>

                    <div className={styles.featuresGrid}>
                        {features.map((f, i) => (
                            <FeatureCard key={i} {...f} />
                        ))}
                    </div>

                    <div className={styles.codeSection}>
                        <span className={styles.sectionLabelSmall}>
                            Coupled Analysis
                        </span>
                        <CodePreview />
                    </div>
                </div>
            </main>
        </Layout>
    );
}
