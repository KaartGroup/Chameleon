import React from "react";
import { NavLink } from "react-router-dom";
import {
  AppBar,
  Toolbar,
  Typography,
  Icon,
  KaartLogo,
  KaartMenuItem,
  ChameleonMenuItem,
  Link,
  Button,
} from "./styles";
import "./styles.css";
import kaartLogo from "../../images/20-KAART-Color.svg";
import { makeStyles } from "@material-ui/core/styles";

const useStyles = makeStyles((theme) => ({
  button: {
    padding: "8px 8px",
  },
  selectedNavLink: {
    backgroundColor: "#4287f5",
    border: 0,
    borderRadius: 3,
    color: "White",
  },
}));

export const Header = () => {
  const classes = useStyles();

  return (
    <AppBar>
      <Toolbar>
        <Typography>
          <Icon>
            <NavLink to="/chameleon">
              <KaartLogo
                src={kaartLogo}
                alt="Kaart Logo"
                href="https://kaart.com/"
              />
            </NavLink>
          </Icon>
        </Typography>
        {/* This is to match kaart.com */}
        <div className="parent-div">
          <KaartMenuItem>
            <div className="dropdown">
              <div className="dropbtn">
                Services
                <i className="arrow"></i>
              </div>
              <div className="dropdown-content">
                <a href="https://kaart.com/osm/">Osm Services</a>
                <a href="https://kaart.com/gis/">Gis Consulting</a>
                <a href="https://kaart.com/dev/">Engineering</a>
              </div>
            </div>
          </KaartMenuItem>
          <KaartMenuItem>
            <div className="dropdown">
              <div href="https://kaart.com/tools/" className="dropbtn">
                Tools<i className="arrow"></i>
              </div>
              <div className="dropdown-content ">
                <a href="http://chameleon.kaart.com/">Chameleon</a>
                <a href="https://gem.kaart.com/">Gem</a>
                <a href="https://github.com/KaartGroup/GoKaart">Gokaart</a>
                <a href="https://simple.kaart.com/">Simple Gis</a>
                <a href="https://viewer.kaart.com/login">Viewer</a>
              </div>
            </div>
          </KaartMenuItem>
          <KaartMenuItem>
            <Link href="https://kaart.com/about/">About</Link>
          </KaartMenuItem>
          <KaartMenuItem>
            <Link href="https://kaart.com/careers/">Careers</Link>
          </KaartMenuItem>
        </div>
        <div className="spacer"></div>
        <ChameleonMenuItem>
          <NavLink to="/chameleon" activeClassName={classes.selectedNavLink}>
            <Button color="inherit" size="large">
              Step-By-Step
            </Button>
          </NavLink>
        </ChameleonMenuItem>
        <ChameleonMenuItem className={classes.ImageHub}>
          <NavLink to="/byod" activeClassName={classes.selectedNavLink}>
            <Button color="inherit" size="large">
              <abbr title="Bring Your Own Data" style={{ textDecoration: "none" }}>BYOD</abbr>
            </Button>
          </NavLink>
        </ChameleonMenuItem>
      </Toolbar>
    </AppBar>
  );
};

