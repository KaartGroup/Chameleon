import React from "react";
import { NavLink } from "react-router-dom";
import {
  AppBar,
  Toolbar,
  Typography,
  Icon,
  KaartLogo,
  KaartMenuItem,
  Link,
} from "./styles";
import "./styles.css";
import kaartLogo from "../../images/20-KAART-Color.svg";

export const Header = () => {
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
        <KaartMenuItem>
          <div class="dropdown">
            <div class="dropbtn">
              Services
              <i class="arrow"></i>
            </div>
            <div class="dropdown-content">
              <a href="https://kaart.com/osm/">Osm Services</a>
              <a href="https://kaart.com/gis/">Gis Consulting</a>
              <a href="https://kaart.com/dev/">Engineering</a>
            </div>
          </div>
        </KaartMenuItem>
        <KaartMenuItem>
          <div class="dropdown">
            <div href="https://kaart.com/tools/" class="dropbtn">
              Tools<i class="arrow"></i>
            </div>
            <div class="dropdown-content ">
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
      </Toolbar>
    </AppBar>
  );
};

