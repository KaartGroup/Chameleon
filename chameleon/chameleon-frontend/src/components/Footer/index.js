import React from "react";
import {
  MainFooter,
  Row,
  Column,
  UI,
  List,
  SmallColumn,
  Header,
  SmallRow,
  Link,
  Social,
  Copyright,
  SocialLink,
  SocialImage,
} from "./styles";

export const Footer = () => {
  return (
    <MainFooter>
      <Row>
        {/* Column1 */}
        <Column>
          <Header>Services</Header>
          <UI>
            <List>
              <Link href="https://kaart.com/osm/">GIS Services</Link>
            </List>
            <List>
              <Link>Software Engineering</Link>
            </List>
            <List>
              <Link href="https://kaart.com/gis/">GIS Consulting</Link>
            </List>
          </UI>
        </Column>
        {/* Column2 */}
        <Column>
          <Header>Tools</Header>
          <UI>
            <List>
              <Link href="https://gem.kaart.com/">GEM</Link>
            </List>
            <List>
              <Link href="https://github.com/KaartGroup/GoKaart">Go Kaart</Link>
            </List>
            <List>
              <Link href="http://chameleon.kaart.com/">Chameleon</Link>
            </List>
          </UI>
        </Column>
        {/* Column3 */}
        <Column>
          <Header>Company</Header>
          <UI>
            <List>
              <Link href="https://kaart.com/about/">About</Link>
            </List>
            <List>
              <Link href="https://kaart.com/careers/">Careers</Link>
            </List>
          </UI>
        </Column>
        {/* Column4 */}
        <Column>
          <Header>Contact</Header>
          <UI></UI>
        </Column>
      </Row>
      <SmallRow>
        <SmallColumn>
          <Copyright>
            &copy;{new Date().getFullYear()} Kaart Group LLC. All rights
            reserved.
          </Copyright>
        </SmallColumn>
        <SmallColumn>
          <Social>
            <SocialLink
              href="https://www.facebook.com/kaartgroup/"
              title="KAART Group Facebook Page"
            >
              <SocialImage
                loading="lazy"
                src="https://kaart.com/wp-content/uploads/2020/08/KG-Facebook-icon.svg"
                width="15"
                height="15"
                alt=""
                class="wp-image-695 alignnone size-medium"
                srcset="https://kaart.com/wp-content/uploads//2020/08/KG-Facebook-icon.svg 150w, 
          https://kaart.com/wp-content/uploads//2020/08/KG-Facebook-icon.svg 300w, 
          https://kaart.com/wp-content/uploads//2020/08/KG-Facebook-icon.svg 1024w, 
          https://kaart.com/wp-content/uploads//2020/08/KG-Facebook-icon.svg 1536w, 
          https://kaart.com/wp-content/uploads//2020/08/KG-Facebook-icon.svg 2048w, 
          https://kaart.com/wp-content/uploads//2020/08/KG-Facebook-icon.svg 40w"
                sizes="(max-width: 15px) 100vw, 15px"
              ></SocialImage>
            </SocialLink>
            <SocialLink
              href="https://github.com/KaartGroup"
              title="KAART Group Github"
            >
              <SocialImage
                loading="lazy"
                src="https://kaart.com/wp-content/uploads/2020/08/KG-GitHub-Icon.svg"
                width="15"
                height="15"
                alt=""
                class="wp-image-696 alignnone size-medium"
                srcset="https://kaart.com/wp-content/uploads//2020/08/KG-GitHub-Icon.svg 150w, 
              https://kaart.com/wp-content/uploads//2020/08/KG-GitHub-Icon.svg 300w, 
              https://kaart.com/wp-content/uploads//2020/08/KG-GitHub-Icon.svg 1024w, 
              https://kaart.com/wp-content/uploads//2020/08/KG-GitHub-Icon.svg 1536w, 
              https://kaart.com/wp-content/uploads//2020/08/KG-GitHub-Icon.svg 2048w, 
              https://kaart.com/wp-content/uploads//2020/08/KG-GitHub-Icon.svg 40w"
                sizes="(max-width: 15px) 100vw, 15px"
              ></SocialImage>
            </SocialLink>
            <SocialLink
              href="https://wiki.openstreetmap.org/wiki/Kaart"
              title="KAART Group WIKI"
            >
              <SocialImage
                loading="lazy"
                src="https://kaart.com/wp-content/uploads/2020/08/KG-WIKI-icon.svg"
                width="32"
                height="15"
                alt=""
                class="wp-image-694 alignnone size-medium"
              ></SocialImage>
            </SocialLink>
            <SocialLink href="https://www.linkedin.com/company/kaart-group/">
              <SocialImage
                loading="lazy"
                src="https://kaart.com/wp-content/uploads/2020/10/iconmonstr-linkedin-1.svg"
                width="15"
                height="15"
                alt=""
                class="wp-image-1457 alignnone size-medium"
                srcset="https://kaart.com/wp-content/uploads//2020/10/iconmonstr-linkedin-1.svg 150w, 
              https://kaart.com/wp-content/uploads//2020/10/iconmonstr-linkedin-1.svg 300w, 
              https://kaart.com/wp-content/uploads//2020/10/iconmonstr-linkedin-1.svg 1024w, 
              https://kaart.com/wp-content/uploads//2020/10/iconmonstr-linkedin-1.svg 1536w,
               https://kaart.com/wp-content/uploads//2020/10/iconmonstr-linkedin-1.svg 2048w, 
               https://kaart.com/wp-content/uploads//2020/10/iconmonstr-linkedin-1.svg 24w"
                sizes="(max-width: 15px) 100vw, 15px"
              ></SocialImage>
            </SocialLink>
          </Social>
        </SmallColumn>
      </SmallRow>
    </MainFooter>
  );
};
