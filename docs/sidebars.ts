import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

const sidebars: SidebarsConfig = {
    docsSidebar: [
        {
            type: "category",
            label: "Getting Started",
            items: [
                "getting-started/installation",
                "getting-started/quickstart",
            ],
        },
        {
            type: "category",
            label: "Disciplines",
            items: [
                "disciplines/naca-airfoil",
                "disciplines/xfoil-analysis",
                "disciplines/oas-vlm",
                "disciplines/oas-aerostruct",
            ],
        },
        {
            type: "category",
            label: "Tutorials",
            items: [
                "tutorials/naca-xfoil-analysis",
                "tutorials/oas-vlm-analysis",
                "tutorials/oas-aerostruct-analysis",
            ],
        },
        {
            type: "category",
            label: "API Reference",
            items: [
                "api/naca-discipline",
                "api/xfoil-discipline",
                "api/oas-discipline",
                "api/oas-aerostruct-disciplines",
            ],
        },
        {
            type: "category",
            label: "About",
            items: [
                "about/license",
                "about/contributing",
            ],
        },
    ],
};

export default sidebars;
