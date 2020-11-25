import React, { useState } from "react";
import ReactGridLayout, { WidthProvider } from "react-grid-layout";

import { Where } from "../Where";
import { When } from "../When";
import { What } from "../What";
import { How } from "../How";
import { FileDetails } from "../FileDetails";
import { SubmitForm } from "../Submit";
import "./styles.css";

const GridLayout = WidthProvider(ReactGridLayout);

export const Chameleon = () => {
    const [layouts, setLayouts] = useState({});

    const onLayoutChange = (layouts) => {
        setLayouts(layouts);
    };

    const getViewHeight = () => {
        return window.innerHeight;
    };

    return (
        <>
            <GridLayout
                measureBeforeMount={true}
                className="layout"
                cols={13}
                containerPadding={[10, 10]}
                rowHeight={getViewHeight() / 2}
                margin={[10, 10]}
                layouts={layouts}
                onLayoutChange={(layout) => onLayoutChange(layout)}
            >
                <div
                    className="where-when"
                    key="1"
                    data-grid={{
                        x: 1,
                        y: 0,
                        w: 3,
                        h: 1,
                        i: "where_when_grid",
                        static: true,
                    }}
                >
                    <Where />
                    <When />
                </div>
                <div
                    className="what"
                    key="2"
                    data-grid={{
                        x: 5,
                        y: 0,
                        w: 3,
                        h: 1,
                        i: "what_grid",
                        static: true,
                    }}
                >
                    <What />
                </div>
                <div
                    className="how-file"
                    key="3"
                    data-grid={{
                        x: 9,
                        y: 0,
                        w: 3,
                        h: 1.269,
                        i: "how_file_grid",
                        static: true,
                    }}
                >
                    <How />
                    <FileDetails />
                </div>
                <div
                    className="submit"
                    key="4"
                    data-grid={{
                        x: 3,
                        y: 1,
                        w: 6,
                        h: 1 / 4,
                        i: "submit_grid",
                        static: true,
                    }}
                >
                    <SubmitForm />
                </div>
            </GridLayout>
        </>
    );
};
