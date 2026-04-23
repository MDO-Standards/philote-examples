import { themes as prismThemes } from "prism-react-renderer";
import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

const config: Config = {
    title: "Philote Examples",
    tagline:
        "Example Philote MDO disciplines for airfoil geometry, aerodynamic analysis, and vortex-lattice methods",
    favicon: "img/favicon.ico",

    future: {
        v4: true,
    },

    url: "https://mdo-standards.github.io",
    baseUrl: "/philote-examples/",

    organizationName: "MDO-Standards",
    projectName: "philote-examples",

    onBrokenLinks: "throw",

    i18n: {
        defaultLocale: "en",
        locales: ["en"],
    },

    stylesheets: [
        {
            href: "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css",
            type: "text/css",
            integrity:
                "sha384-nB0miv6/jRmo5RLHO8BIp/8hwC1slNFDuv3VUgI4A7O/lEKmpRgiuNOQI2bRpFB",
            crossorigin: "anonymous",
        },
    ],

    presets: [
        [
            "classic",
            {
                docs: {
                    sidebarPath: "./sidebars.ts",
                    remarkPlugins: [remarkMath],
                    rehypePlugins: [rehypeKatex],
                    editUrl:
                        "https://github.com/MDO-Standards/philote-examples/tree/develop/docs/",
                    lastVersion: "0.2.0",
                    versions: {
                        current: {
                            label: "Next",
                        },
                    },
                },
                blog: false,
                theme: {
                    customCss: "./src/css/custom.css",
                },
            } satisfies Preset.Options,
        ],
    ],

    themeConfig: {
        colorMode: {
            defaultMode: "dark",
            respectPrefersColorScheme: true,
        },
        navbar: {
            title: "Philote Examples",
            items: [
                {
                    type: "docSidebar",
                    sidebarId: "docsSidebar",
                    position: "left",
                    label: "Docs",
                },
                {
                    type: "docsVersionDropdown",
                    position: "right",
                },
                {
                    href: "https://github.com/MDO-Standards/philote-examples",
                    label: "GitHub",
                    position: "right",
                },
            ],
        },
        footer: {
            style: "dark",
            links: [
                {
                    title: "Documentation",
                    items: [
                        {
                            label: "Getting Started",
                            to: "/docs/getting-started/installation",
                        },
                        {
                            label: "Quick Start",
                            to: "/docs/getting-started/quickstart",
                        },
                        {
                            label: "Tutorials",
                            to: "/docs/tutorials/naca-xfoil-analysis",
                        },
                    ],
                },
                {
                    title: "More",
                    items: [
                        {
                            label: "GitHub",
                            href: "https://github.com/MDO-Standards/philote-examples",
                        },
                        {
                            label: "Philote-Python",
                            href: "https://mdo-standards.github.io/Philote-Python/",
                        },
                        {
                            label: "PyPI",
                            href: "https://pypi.org/project/philote-examples/",
                        },
                    ],
                },
            ],
            copyright: `Copyright \u00A9 2024-${new Date().getFullYear()} Christopher A. Lupp. Built with Docusaurus.`,
        },
        prism: {
            theme: prismThemes.github,
            darkTheme: prismThemes.dracula,
            additionalLanguages: ["python", "bash"],
        },
    } satisfies Preset.ThemeConfig,
};

export default config;
