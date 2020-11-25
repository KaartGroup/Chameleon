import React, { useState } from "react";
import ReactGridLayout, { WidthProvider } from "react-grid-layout";

import { Where } from "../Where";
import { When } from "../When";
import { What } from "../What";
import { How } from "../How";
import { FileDetails } from "../FileDetails";
import "./styles.css";

const GridLayout = WidthProvider(ReactGridLayout);

export const Chameleon = () => {
  const [layouts, setLayouts] = useState({});

  const onLayoutChange = (layouts) => {
    setLayouts(layouts);
  };

  const getViewHeight = () => {
    return window.innerHeight - 130;
  };


  return (
    <div className="chameleon">
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
        className="where"
        key="1"
        style={{ display: "grid", justifyContent: "center" }}
        data-grid={{
          x: 1,
          y: 0,
          w: 3,
          h: 1,
          i: "where_grid",
          static: true,
          }}
        >
          <Where />
        </div>
        <div
          className="when"
          key="2"
          style={{ display: "grid", justifyContent: "center" }}
          data-grid={{
            x: 5,
            y: 0,
            w: 3,
            h: 1,
            i: "when_grid",
            static: true,
            }}
          >
            <When />
          </div>
          <div
            className="what"
            key="3"
            style={{ display: "grid", justifyContent: "center" }}
            data-grid={{
              x: 9,
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
            className="how"
            key="4"
            style={{ display: "grid", justifyContent: "center" }}
            data-grid={{
              x: 3,
              y: 1,
              w: 3,
              h: 1,
              i: "how_grid",
              static: true,
            }}
          >
            <How />
          </div>
          <div
            className="file"
            key="5"
            style={{ display: "grid", justifyContent: "center" }}
            data-grid={{
              x: 7,
              y: 1,
              w: 3,
              h: 1,
              i: "file_grid",
              static: true,
            }}
          >
            <FileDetails />
          </div>
      </GridLayout>
    </div>
  );
};
